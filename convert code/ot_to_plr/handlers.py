import re
from matchers import match_regex_pattern
from expanders import expand_regex_operation, expand_list_comprehension

def handle_for_loop(lines, i, indent, loop_var, total_col):
    """
    处理for循环，展开每个循环的具体内容
    """
    body = []
    i += 1  # Move to the next line
    while i < len(lines) and (lines[i].startswith(indent + '    ') or lines[i].strip() == ''):
        body_line = lines[i][len(indent)+4:] if lines[i].strip() != '' else ''
        body.append(body_line)
        i += 1
    
    expanded_body = []
    for n in range(total_col):
        expanded_body.append(f'{indent}# Loop {loop_var} = {n}')
        for bline in body:
            # 检查是否是正则表达式操作
            regex_match = match_regex_pattern(f"{indent}{bline}")
            if regex_match:
                expanded_line = expand_regex_operation(bline, loop_var, n)
            else:
                expanded_line = re.sub(rf'\b{loop_var}\b', str(n), bline)
            expanded_body.append(f'{indent}{expanded_line}')
    
    return expanded_body, i

def handle_list_comprehension(lines, i, listcomp_match):
    """
    处理列表推导式，展开为多个行
    """
    indent = listcomp_match.group(1)
    var_name = listcomp_match.group(2)
    expr = listcomp_match.group(3).strip()
    loop_var = listcomp_match.group(4)
    list_str = listcomp_match.group(5)
    
    try:
        slots = eval(list_str, {"__builtins__": None}, {})
    except Exception:
        return [lines[i]], i
    
    expanded_code = expand_list_comprehension(f'{var_name} = [{expr} for {loop_var} in {list_str}]')
    return [f'{indent}{line}' for line in expanded_code], i + 1

def handle_regex_operation(lines, i, regex_match):
    """
    处理正则表达式操作
    """
    indent = regex_match.group(1)
    var_name = regex_match.group(2)
    regex_func = regex_match.group(3)
    args = regex_match.group(4)
    
    # 直接返回原行，在for循环展开时会处理变量替换
    return [lines[i]], i + 1