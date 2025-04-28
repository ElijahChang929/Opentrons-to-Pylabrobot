import re
import ast

def expand_regex_operation(line, loop_var=None, loop_value=None):
    """
    展开正则表达式操作，替换其中的循环变量
    """
    if loop_var and loop_value is not None:
        # 替换循环变量
        return re.sub(rf'\b{loop_var}\b', str(loop_value), line)
    return line

def expand_list_comprehension(code: str):
    """
    展开列表推导式的函数
    """
    tree = ast.parse(code)
    
    if isinstance(tree.body[0], ast.Assign):
        value = tree.body[0].value
        if isinstance(value, ast.ListComp):
            element = value.elt
            for_loop = value.generators[0]
            iter_var = for_loop.target.id
            iter_list = ast.literal_eval(for_loop.iter)
            
            expanded_code = []
            for item in iter_list:
                if isinstance(element.func, ast.Attribute):
                    base = element.func.value.id  # ctx
                    func = element.func.attr  # load_labware
                    args = []
                    for arg in element.args:
                        if isinstance(arg, ast.Constant):
                            args.append(str(arg.value))
                        elif isinstance(arg, ast.Name):
                            args.append(arg.id)
                        else:
                            args.append(str(arg))
                else:
                    base = element.func.id
                    func = element.func.id
                    args = [str(arg) for arg in element.args]
                
                expanded_code.append(f"{base}.{func}({', '.join(args + [str(item)])})")
            
            return expanded_code

def expand_tiprack(match):
    """
    专门处理tiprack这样的特殊情况
    """
    indent = match.group(1)
    var_name = match.group(2)
    labware_type = match.group(3)
    slot_var = match.group(4)
    slots_str = match.group(5)
    
    try:
        slots = eval(slots_str)
        result = [f"{indent}{var_name} = []"]
        for slot in slots:
            result.append(f"{indent}{var_name}.append(ctx.load_labware('{labware_type}', {slot}))")
        return '\n'.join(result)
    except Exception as e:
        print(f"Error expanding tiprack: {e}")
        return match.group(0)  # 返回原始文本