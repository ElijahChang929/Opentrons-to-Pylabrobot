# Read the contents of test.txt
file_path = "test.txt"


# delete rows if they contain the string Blowing, Moving, Dispensing, Aspirating
with open(file_path, "r") as file:
    lines = file.readlines()
    lines = [line for line in lines if not any(
        word in line for word in ["Blowing", "Moving", "Dispensing", "Aspirating","Transferring"])]
    lines = [line for line in lines if not any(
        word in line for word in ["pick_up_tip", "drop_tip", "return_tip"])]
    lines = [line for line in lines if not any(
        word in line for word in ["aspirate", "dispense", "mix", "blow_out"])]
    lines = [line for line in lines if not any(
        word in line for word in ["touch_tip", "slow_withdraw", "delay"])]

with open("filtered_test.txt", "w") as outfile:
    for line in lines:
        outfile.write(line)
