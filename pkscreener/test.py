import sys
import os

print("Python Executable:", sys.executable)
print("Python Path:")
for p in sys.path:
    print(" ", p)

try:
    import PKDevTools
    print("Success! PKDevTools imported.")
except ModuleNotFoundError as e:
    print("Error:", e)