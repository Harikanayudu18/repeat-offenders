"""Real TabPFN integration. Never returns a score unless TabPFNClassifier actually fit+predicted."""
import importlib.metadata
import numpy as np


class ModelUnavailable(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


class TabPFNAdapter:
    name = "TabPFN"

    def __init__(self, device: str = "cpu"):
        self.device = device
        self._failed = None  # cached (code, message) after an init failure

    def status(self) -> dict:
        try:
            import tabpfn  # noqa: F401
            ver = importlib.metadata.version("tabpfn")
        except ImportError:
            return {"available": False, "code": "package_missing",
                    "message": "tabpfn package not installed (pip install tabpfn; see docs/MODEL_SETUP.md)"}
        if self._failed:
            return {"available": False, "code": self._failed[0], "message": self._failed[1], "package_version": ver}
        return {"available": True, "code": "ok", "package_version": ver, "device": self.device,
                "note": "weights/licence access is verified at first fit"}

    def score(self, Xtr, ytr, Xte) -> np.ndarray:
        st = self.status()
        if not st["available"]:
            raise ModelUnavailable(st["code"], st["message"])
        if len(set(np.asarray(ytr).tolist())) < 2:
            raise ModelUnavailable("single_class", "training labels contain a single class")
        try:
            from tabpfn import TabPFNClassifier
            clf = TabPFNClassifier(device=self.device)
            clf.fit(np.asarray(Xtr, dtype=float), np.asarray(ytr))
            proba = clf.predict_proba(np.asarray(Xte, dtype=float))
            idx = list(clf.classes_).index(1)
            return proba[:, idx]
        except MemoryError:
            self._failed = ("out_of_memory", "TabPFN ran out of memory")
        except Exception as e:  # weights missing, licence not accepted, incompatible API...
            self._failed = ("init_or_inference_failed", f"{type(e).__name__}: {str(e)[:200]}")
        raise ModelUnavailable(*self._failed)
