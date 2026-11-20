import functools

from redstone import fileformat

# One load per spec per pytest process, shared by every module that walks the whole library
# (a full load takes most of a minute). Callers must not mutate what it returns.
load = functools.cache(fileformat.load)
