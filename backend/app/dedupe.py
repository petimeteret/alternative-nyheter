from datasketch import MinHash, MinHashLSH
import re

TOKEN_RE = re.compile(r"\w+", re.U)

class DupeFilter:
    def __init__(self, threshold: float = 0.85):
        self.lsh = MinHashLSH(threshold=threshold, num_perm=128)
        self.index = {}

    @staticmethod
    def _signature(text: str) -> MinHash:
        m = MinHash(num_perm=128)
        for tok in TOKEN_RE.findall((text or "").lower()):
            m.update(tok.encode("utf-8"))
        return m

    def seen(self, key: str, text: str):
        sig = self._signature(text)
        cand = self.lsh.query(sig)
        hexsig = sig.hashvalues.tobytes().hex()
        if cand:
            return True, hexsig
        self.lsh.insert(key, sig)
        self.index[key] = hexsig
        return False, hexsig
