# This module defines the Imports dictionary to track optional dependencies availability

Imports = {}

try:
    import talib
    Imports["talib"] = True
except ImportError:
    Imports["talib"] = False

try:
    import pandas_ta
    Imports["pandas_ta"] = True
except ImportError:
    Imports["pandas_ta"] = False

try:
    import keras
    Imports["keras"] = True
except ImportError:
    Imports["keras"] = False

try:
    import scipy
    Imports["scipy"] = True
except ImportError:
    Imports["scipy"] = False

try:
    import vectorbt
    Imports["vectorbt"] = True
except ImportError:
    Imports["vectorbt"] = False
