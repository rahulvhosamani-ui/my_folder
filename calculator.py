"""A simple command-line calculator."""
def subtract(a, b):
    return a - b


def calculate(left, operator, right):
	"""Apply an arithmetic operator to two numbers."""
	operations = {
		"+": lambda: left + right,
		"-": lambda: left - right,
		"*": lambda: left * right,
		"/": lambda: left / right,
	}
	if operator not in operations:
		raise ValueError("Use one of: +, -, *, /.")
	if operator == "/" and right == 0:
		raise ZeroDivisionError("Cannot divide by zero.")
	return operations[operator]()


def main():
	print("Calculator: enter expressions like 12 + 3 (or q to quit).")
	while True:
		expression = input("> ").strip()
		if expression.lower() in {"q", "quit", "exit"}:
			return

		parts = expression.split()
		if len(parts) != 3:
			print("Enter an expression in the form: number operator number")
			continue

		try:
			result = calculate(float(parts[0]), parts[1], float(parts[2]))
		except (ValueError, ZeroDivisionError) as error:
			print(f"Error: {error}")
		else:
			print(result)


if __name__ == "__main__":
	main()
