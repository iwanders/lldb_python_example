
# Helper to parse /proc/<PID>/maps
# https://www.kernel.org/doc/html/latest/filesystems/proc.html
#address           perms offset  dev   inode      pathname


t = """
003ff000-00400000 rwxp 00000000 00:00 0 
00400000-0040d000 r-xp 00000000 fd:01 85462701                           /tmp/Game.exe
"""
from collections import namedtuple

Region = namedtuple("Region", ["address", "perms", "offset", "dev", "inode", "pathname"])

def get_process_maps(pid):
    with open("/proc/{}/maps".format(pid), "rt") as f:
        d = f.readlines()
    res = []
    for l in d:
        # but of course we have spaces in the paths...
        def tokenizer(l):
            l = l
            def z(t=" "):
                nonlocal l
                if t is None:
                    return l
                if t in l:
                    index = l.find(t)
                    r = l[0:index]
                    l = l[index+1:]
                else:
                    return None
                return r
            return z
        t = tokenizer(l)
        address = tuple(int(v, 16) for v in t().split("-"))
        perms = t()
        offset = int(t(), 16)
        dev = t()
        inode = int(t(), 16)
        pathname = None
        if l:
            pathname = t(None).strip()
        res.append(Region(address=address,
                          perms=perms,
                          offset=offset,
                          dev=dev,
                          inode=inode,
                          pathname=pathname))
    return res


if __name__ == "__main__":
    import sys
    maps = get_process_maps(sys.argv[1])
    for r in maps:
        print(r)
