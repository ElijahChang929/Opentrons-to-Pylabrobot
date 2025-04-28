import re
from pathlib import PosixPath
from matchers import match_for_loop, match_regex_pattern
from expanders import expand_tiprack
from handlers import handle_for_loop, handle_list_comprehension, handle_regex_operation

def transform_explicit(code):
    """
    主函数，处理整个代码的转换
    """
    if isinstance(code, PosixPath):
        with code.open('r', encoding='utf-8') as f:
            code = f.read()
    
    total_col = 12  # Total columns
    
    # 预处理：单独处理 tiprack 这样的特殊跨行列表推导式
    tiprack_pattern = re.compile(r'(\s*)(\w+)\s*=\s*\[\s*ctx\.load_labware\([\'"]([^\'"]+)[\'"]\s*,\s*(\w+)\s*\)\s*\n\s*for\s+\4\s+in\s+(\[[\d\s,]+\])\s*\]')
    code = tiprack_pattern.sub(lambda m: expand_tiprack(m), code)
    
    # 预处理：合并其他多行列表推导式
    lines = code.split('\n')
    i = 0
    merged_lines = []
    
    while i < len(lines):
        line = lines[i].rstrip()
        # 检查是否是列表推导式的开始 (更宽松的条件)
        if '=' in line and '[' in line and ']' not in line and 'for' in line:
            # 捕获变量名和缩进
            match = re.match(r'^(\s*)(\w+)\s*=\s*\[(.*)$', line)
            if match:
                indent = match.group(1)
                var_name = match.group(2)
                expr_start = match.group(3)
                
                # 收集整个列表推导式
                full_expr = expr_start
                i += 1
                while i < len(lines) and ']' not in lines[i]:
                    full_expr += ' ' + lines[i].strip()
                    i += 1
                
                if i < len(lines):  # 添加包含']'的最后一行
                    full_expr += ' ' + lines[i].strip()
                
                # 重构完整的列表推导式
                merged_lines.append(f"{indent}{var_name} = [{full_expr}")
            else:
                merged_lines.append(line)
        else:
            merged_lines.append(line)
        i += 1
    
    # 使用合并后的行进行处理
    transformed = []
    i = 0
    lines = merged_lines
    
    # 更灵活的列表推导式匹配模式
    listcomp_pattern = re.compile(r'^(\s*)(\w+)\s*=\s*\[\s*(.*?)\s+for\s+(\w+)\s+in\s+(\[.*?\])\s*\]\s*$')
    
    while i < len(lines):
        line = lines[i]
        # 调试输出
        #print(f"Processing line {i}: {line[:80]}...")
        
        loop_match = match_for_loop(line)
        listcomp_match = listcomp_pattern.match(line)
        regex_match = match_regex_pattern(line)
        
        if loop_match:
            indent = loop_match.group(1)
            loop_var = loop_match.group(2)
            expanded_body, i = handle_for_loop(lines, i, indent, loop_var, total_col)
            transformed.extend(expanded_body)
        
        elif listcomp_match:
            # 打印调试信息
            print(f"Found list comprehension: {listcomp_match.groups()}")
            
            # 提取列表推导式信息
            indent = listcomp_match.group(1)
            var_name = listcomp_match.group(2)
            expr = listcomp_match.group(3).strip()
            loop_var = listcomp_match.group(4)
            list_str = listcomp_match.group(5)
            
            try:
                # 解析迭代对象为列表
                slots = eval(list_str, {"__builtins__": {}}, {})
                
                # 生成初始化列表的代码
                transformed.append(f"{indent}{var_name} = []")
                
                # 特殊处理 tiprack 这样的情况
                if "ctx.load_labware" in expr:
                    # 尝试匹配 ctx.load_labware 调用
                    labware_match = re.search(r"ctx\.load_labware\(['\"]([^'\"]+)['\"],\s*(\w+)([^)]*)\)", expr)
                    
                    if labware_match:
                        labware_type = labware_match.group(1)
                        slot_var = labware_match.group(2)
                        extra_args = labware_match.group(3) if labware_match.group(3) else ''
                        
                        # 为每个槽位生成一个 append 语句
                        for slot in slots:
                            transformed.append(
                                f"{indent}{var_name}.append(ctx.load_labware('{labware_type}', {slot}{extra_args}))"
                            )
                    else:
                        # 如果无法解析，回退到简单替换
                        for slot in slots:
                            expanded_expr = re.sub(rf'\b{loop_var}\b', str(slot), expr)
                            transformed.append(f"{indent}{var_name}.append({expanded_expr})")
                else:
                    # 处理一般情况
                    for slot in slots:
                        expanded_expr = re.sub(rf'\b{loop_var}\b', str(slot), expr)
                        transformed.append(f"{indent}{var_name}.append({expanded_expr})")
            
            except Exception as e:
                # 发生错误时保留原始行
                transformed.append(line)
                print(f"Error expanding list comprehension: {e}")
            
            i += 1
        
        elif regex_match:
            # 打印调试信息
            print(f"Found regex operation: {regex_match.groups()}")
            expanded_code, i = handle_regex_operation(lines, i, regex_match)
            transformed.extend(expanded_code)
        
        else:
            transformed.append(line)
            i += 1
    
    return '\n'.join(transformed)