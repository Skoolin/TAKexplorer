from typing import NewType


TpsSymmetry = NewType("TpsSymmetry", int)
TpsString = NewType("TpsString", str) # with xn collapsed (x,x,x,... -> xn)
TpsStringExpanded = NewType("TpsStringExpanded", str) # with xn expanded to x,x,x...
NormalizedTpsString = NewType("NormalizedTpsString", str)
BoardSize = NewType("BoardSize", int)
