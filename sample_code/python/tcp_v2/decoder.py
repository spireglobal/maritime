from pyais import decode_msg
from pyais import exceptions as pe
from loguru import logger as log
from keys import decode_keys
import datetime


def parse_raw(lines):
    """Parses the TCP lines/messages
    :param lines: Messages / lines from TCP stream
    :type lines: list
    :returns: list of dictionaries w decoded messages and tags
    :rtype: list
    """
    result: list = list()
    for i in range(len(lines) - 3):  # ensure no index errors at the end of the list of lines - 3
        encoded: list = list()
        line: str = lines[i]
        line = _clean_line(line)
        # Get message portion (exclude tags)
        first_line = _get_message_portion(line)
        # Get the tags, exclude message
        c_tag, s_tag, g_tag = _extract_tags(line)

        # Handle single line messages
        if not g_tag:
            not_decoded: dict = _normalize_dict(dict(),
                                                c_tag,
                                                s_tag,
                                                g_tag,
                                                g_tag_part='',
                                                g_tag_total_parts='',
                                                g_tag_id='',
                                                raw_message=first_line)

            try:
                # Decoded message is in a dictionary
                decoded: dict = decode_msg(first_line)

            except pe.InvalidNMEAMessageException as e:
                msg = f"""
                line: {line}
                {e}
                """
                log.error(msg)
            finally:
                complete: dict = _add_decoded_and_non_decoded(not_decoded, decoded)
                result.append(complete)

        # Handle multi-line messages        
        else:
            # Already have: line, first_line, c_tag, s_tag, g_tag
            # Parse the group tag part-parts-id
            g_tag_part, g_tag_total_parts, g_tag_id = _parse_g_tag(g_tag)
            if g_tag_part == '1':
                non_decoded: dict = _normalize_dict(dict(),
                                                    c_tag,
                                                    s_tag,
                                                    g_tag,
                                                    g_tag_part,
                                                    g_tag_total_parts,
                                                    g_tag_id,
                                                    raw_message=first_line)

                # Nothing to decode for the first line
                complete: dict = _add_decoded_and_non_decoded(non_decoded, decoded=None)
                result.append(complete)

                # Get second line, there have to be at least 2
                second_message = _clean_line(lines[i + 1])
                # Get the tags from the second line, only the g_tag should be there
                c_tag, s_tag, g_tag = _extract_tags(second_message)
                # Parse the group tag
                g_tag_part, g_tag_total_parts, g_tag_id2 = _parse_g_tag(g_tag)

                # Add check to ensure the next part is in the same group
                # g_tag_id2 == g_tag_id

                if g_tag_part == '2' and g_tag_id2 == g_tag_id:
                    # Get the second message portion (exclude tags)
                    second_line = _get_message_portion(second_message)

                    non_decoded = _normalize_dict(dict(),
                                                  c_tag,
                                                  s_tag,
                                                  g_tag,
                                                  g_tag_part,
                                                  g_tag_total_parts,
                                                  g_tag_id,
                                                  raw_message=second_line)

                    # If this is the last line, decode
                    if g_tag_total_parts == '2':
                        try:
                            decoded = decode_msg(first_line, second_line)
                        except pe.InvalidNMEAMessageException as e:
                            msg = f"""
                            line: {line}
                            {e}
                            """
                            log.error(msg)
                            continue

                        complete: dict = _add_decoded_and_non_decoded(non_decoded, decoded)
                        add_this = _normalize_dict(complete,
                                                   c_tag,
                                                   s_tag,
                                                   g_tag,
                                                   g_tag_part,
                                                   g_tag_total_parts,
                                                   g_tag_id,
                                                   raw_message=second_line)
                        result.append(add_this)
                        continue

                    # Get the third line
                    third_line = lines[i + 2]
                    c_tag, s_tag, g_tag = _extract_tags(third_line)
                    g_tag_part, g_tag_total_parts, g_tag_id3 = _parse_g_tag(g_tag)

                    if g_tag_part == '3' and g_tag_id3 == g_tag_id:
                        non_decoded = _normalize_dict(dict(),
                                                      c_tag,
                                                      s_tag,
                                                      g_tag,
                                                      g_tag_part,
                                                      g_tag_total_parts,
                                                      g_tag_id,
                                                      raw_message=third_line)

                        # The limit is 3 parts, so decode
                        try:
                            decoded = decode_msg(first_line, second_line)
                        except pe.InvalidNMEAMessageException as e:
                            msg = f"""
                            line: {line}
                            {e}
                            """
                            log.error(msg)
                            continue

                        complete: dict = _add_decoded_and_non_decoded(
                            non_decoded, decoded)
                        add_this = _normalize_dict(complete,
                                                   c_tag,
                                                   s_tag,
                                                   g_tag,
                                                   g_tag_part,
                                                   g_tag_total_parts,
                                                   g_tag_id,
                                                   raw_message=third_line)
                        result.append(add_this)
                        continue

    return result


def _extract_tags(line: str):
    """Examines the message to parse out the tags
    :param line: Single text line of TCP stream
    :type line: str
    :returns: c_tag, s_tag, g_tag
    :rtype: str, str, str
    """
    # \g:2-2-0*6D\!AIVDM,2,2,0,A,00000000000,2*24
    c_tag: str = ''
    s_tag: str = ''
    g_tag: str = ''
    parts: list = line.split(',')
    for part in parts:
        # Remove slashes
        clean1 = part.replace("\\\\", "")
        clean2 = clean1.replace("\\", "")
        part = clean2
        # Get tag
        if 's:' in part:
            s_tag = part.replace("s:", "")
        elif 'c:' in part:
            c_tag = part.replace("c:", "")
            c_tag = c_tag[:10]
        elif 'g:' in part:
            g_tag = part.replace("g:", "")
            # Clean up the trailing trash 2-2-0*6D!AIVDM
            asterisk_location = g_tag.find("*")
            if asterisk_location > 0:
                g_tag = g_tag[:asterisk_location]
    return c_tag, s_tag, g_tag


def _get_message_portion(line):
    bang_location = line.find('!')
    # Get the message portion
    return line[bang_location:]


def _parse_g_tag(g_tag):
    g_tag_part = ''
    g_tag_total_parts = ''
    g_tag_id = ''

    # Helps avoid 'last message' index error
    if '-' not in g_tag:
        return g_tag_part, g_tag_total_parts, g_tag_id

    # Get each element from group tag
    elements: list = g_tag.split('-')
    try:
        g_tag_part = elements[0]
        g_tag_total_parts = elements[1]
        g_tag_id = elements[2]
    except IndexError as e:
        msg = f"""
        g_tag: {g_tag}
        elements: {elements}
        """
        log.error(msg)
    return g_tag_part, g_tag_total_parts, g_tag_id


def _clean_line(line):
    replace_list = ["EpfdType.",
                    "\r",
                    "\n",
                    "NavigationStatus.",
                    "ShipType.",
                    "ManeuverIndicator."]
    for item in replace_list:
        line.replace(item, "")
    return line


def _normalize_dict(dictionary: dict,
                    c_tag: str,
                    s_tag: str,
                    g_tag: str,
                    g_tag_part: str,
                    g_tag_total_parts: str,
                    g_tag_id: str,
                    raw_message: str = ''):
    dictionary['internal_timestamp'] = "AUTO"
    dictionary['msg_time'] = _handle_time(c_tag)
    dictionary['c_tag'] = c_tag
    dictionary['s_tag'] = s_tag
    dictionary['g_tag'] = g_tag
    dictionary['g_tag_part'] = g_tag_part
    dictionary['g_tag_total_parts'] = g_tag_total_parts
    dictionary['g_tag_id'] = g_tag_id
    dictionary['raw_message'] = raw_message
    for k in decode_keys:
        dictionary.setdefault(k.lower(), '')
    return dictionary


def _add_decoded_and_non_decoded(non_decoded: dict, decoded: dict):
    if not decoded:
        return non_decoded
    else:
        for k, v in decoded.items():
            v = str(v)
            non_decoded[k] = v.lower()
    return non_decoded


def _handle_time(stamp):
    """
    Converts stamp to datetime
    """
    if type(stamp) == str and stamp:
        try:
            result = datetime.datetime.fromtimestamp(int(stamp)).strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            return ''
    elif stamp:
        try:
            result = stamp.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            return ''
    else:
        return ''
    return result
