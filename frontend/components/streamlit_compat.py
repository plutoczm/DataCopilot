class _NoopStreamlit:
    session_state: dict = {}

    def __getattr__(self, name):
        def _noop(*args, **kwargs):
            if name in {"button", "form_submit_button", "checkbox"}:
                return False
            if name in {"text_area", "text_input", "selectbox"}:
                return kwargs.get("value") or (args[1] if len(args) > 1 else "")
            if name == "slider":
                return kwargs.get("value", 5)
            if name == "file_uploader":
                return None
            if name == "columns":
                count = args[0] if args else 1
                if isinstance(count, int):
                    return [self for _ in range(count)]
                return [self for _ in count]
            if name in {"tabs"}:
                return [self for _ in (args[0] if args else [])]
            if name in {"container", "form", "expander", "spinner", "chat_message"}:
                return self
            return None

        return _noop

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


try:
    import streamlit as st
except ModuleNotFoundError:
    st = _NoopStreamlit()


__all__ = ["st"]
