import uvicorn
from app.config import get_config

_cfg = get_config()
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=_cfg['app']['port'], reload=True)