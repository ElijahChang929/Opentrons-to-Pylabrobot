import ast
from typing import List, Dict, Tuple, Any
import json
import re
class OTAnalyzer(ast.NodeVisitor):
    """Walk an OT-2 protocol script and collect semantic info."""
    def __init__(self, source: str):
        self.labware: List[Tuple[str, str, str]] = []    # [(var, load_name, slot)]
        self.tipracks: Dict[str, str] = {}               # var -> slot
        self.pipettes: Dict[str, Dict[str, Any]] = {}    # var -> {...}
        self.steps: List[ast.Call] = []                  # pipetting calls
        self.source = source    
        self.variables: Dict[str, Any] = {}     # ★ 所有已解析的变量
        self.run_constants: Dict[str, Any] = {} # ★ Constants defined in run() function
        self._extract_json_values()             # ★ 先解析 get_values 里的 JSON

    def _extract_json_values(self):
        """
        寻找 get_values() 函数中 json.loads(\"\"\"{...}\"\"\") 的 JSON 字符串，
        转成字典后存到 self.variables_default
        """
        # 粗暴正则抓第一个 {...}
        m = re.search(r'json\.loads\(\s*"""\s*({.*?})\s*"""\s*\)', self.source, flags=re.S)
        if not m:
            self.variables_default = {}
            return
        try:
            self.variables_default = json.loads(m.group(1))
        except Exception as err:
            print(f"[WARN] JSON解析失败: {err}")
            self.variables_default = {}

    # ------ helpers ------
    def _const(self, node):
        if isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.Str):  # For older Python versions
            return node.s
        elif isinstance(node, ast.Name):
    # 变量替换：若已解析出真实值就返回，否则返回变量名字符串
            return self.variables.get(node.id, node.id)
        else:
            print(f"[DEBUG] Unexpected node type in _const: {ast.dump(node)}")
            raise ValueError("Expect constant")

    # ------ visit methods ------
    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Capture the run function to extract constants defined inside it
        if node.name == "run":
            for stmt in node.body:
                if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                    var_name = stmt.targets[0].id
                    if isinstance(stmt.value, ast.Constant):
                        # For simple constants like TOTAL_COl = 12
                        self.run_constants[var_name] = stmt.value.value
                    elif isinstance(stmt.value, (ast.Num, ast.Str)):
                        # For Python 3.7 and earlier
                        self.run_constants[var_name] = stmt.value.n if isinstance(stmt.value, ast.Num) else stmt.value.s
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Attribute):
            func_val = node.func.value
            fname = node.func.attr  
            tgt = func_val.id if isinstance(func_val, ast.Name) else None  
            
            # 1) labware
            if tgt == "ctx" and fname == "load_labware":
                raw_load_name = self._const(node.args[0])  # Get the load_name (labware)
                load_name = self.variables.get(raw_load_name, raw_load_name) if isinstance(raw_load_name, str) else raw_load_name
                slot = self._const(node.args[1])  # Get the slot

                # Get the variable name (varname)
                if node.keywords:
                    varname = self._const(node.keywords[0].value)
                else:
                    varname = f"{load_name}_{slot}"

                # Avoid naming conflicts like opentrons_96_tiprack_300ul_slot
                if varname.endswith(f"_{slot}"):
                    varname = varname[:-len(f"_{slot}")]

                # Append to labware list (varname, load_name, slot)
                self.labware.append((varname, load_name, slot))
                print(self.labware)
            # Handle list comprehension: tiprack = [ctx.load_labware(...) for slot in [...] ]
            elif isinstance(node.func, ast.Name) and fname == "load_labware" and isinstance(node.args[0], ast.Str) and isinstance(node.args[1], ast.Name):
                # Parse list comprehensions by visiting individual `ctx.load_labware` calls
                for element in node.args[1].elts:  # Iterating over the list of slots
                    slot = self._const(element)
                    raw_load_name = self._const(node.args[0])  # Get the load_name (labware)
                    load_name = self.variables.get(raw_load_name, raw_load_name) if isinstance(raw_load_name, str) else raw_load_name
                    varname = f"{load_name}_{slot}"
                    self.labware.append((varname, load_name, slot))

            # Handle `assign_child_at_slot`
            elif tgt == "ctx" and fname == "assign_child_at_slot":

                parent = self._const(node.args[0])
                child = self._const(node.args[1])
                slot = self._const(node.args[2])
                # Ensure correct naming: parent_slot_child
                varname = f"{parent}_{slot}_{child}"
                self.labware.append((varname, child, slot))
                print(f"[DEBUG] Assigning child labware: {varname} -> {child} at slot {slot}")

            # 2) instrument - 修改这部分
            elif tgt == "ctx" and fname == "load_instrument":
                model = self._const(node.args[0])
                mount = self._const(node.keywords[0].value)
                var = ast.get_source_segment(self.source, node).split('=')[0].strip()
                
                # Skip generating ctx.load_instrument line since we'll use lh.setup_pipette
                # self.pipettes[var] = {"model": model, "mount": mount, "tip_racks": []}
                return

            # 3) Handle other pipetting methods like transfer, aspirate, dispense, etc.
            elif fname in {"transfer", "aspirate", "dispense", "mix", "pick_up_tip", "drop_tip"}:
                self.steps.append(node)

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            if node.value.func.id == "get_values":
                keys = [self._const(arg) for arg in node.value.args]
                if len(node.targets) == 1 and isinstance(node.targets[0], (ast.Tuple, ast.List)):
                    targets = [t.id for t in node.targets[0].elts]
                else:
                    targets = [t.id for t in node.targets]
                for var_name, key in zip(targets, keys):
                    if key in self.variables_default:
                        self.variables[var_name] = self.variables_default[key]
                #print("[DEBUG] 当前收集到的变量:", self.variables)  # 🔥加在这里
                return
        self.generic_visit(node)
