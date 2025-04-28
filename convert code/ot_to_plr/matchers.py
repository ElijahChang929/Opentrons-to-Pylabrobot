import re

def match_for_loop(line):
    """
    匹配for循环模式，例如：for i in range(TOTAL_COl):
    """
    return re.match(r'^(\s*)for\s+([a-z])\s+in\s+range\(TOTAL_COl\):\s*$', line)

def match_regex_pattern(line):
    """
    匹配正则表达式模式，例如：re.match(r'pattern', string)
    """
    return re.match(r'^(\s*)(.+?)\s*=\s*re\.(match|search|findall|sub)\((.*)\)\s*$', line)