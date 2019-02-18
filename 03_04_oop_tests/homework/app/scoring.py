import hashlib
import json

from store import Store


def get_score(store: Store, phone, email, birthday=None, gender=None, first_name=None, last_name=None) -> float:
    key_parts = [
        first_name or "",
        last_name or "",
        birthday.strftime("%Y%m%d") if birthday is not None else "",
    ]
    key = "".join(key_parts).encode()
    key = "uid:" + hashlib.md5(key).hexdigest()
    # try get from cache,
    # fallback to heavy calculation in case of cache miss
    score = store.cache_get(key) or 0
    if score:
        return float(score)
    if phone:
        score += 1.5
    if email:
        score += 1.5
    if birthday and gender:
        score += 1.5
    if first_name and last_name:
        score += 0.5
    # cache for 60 minutes
    store.cache_set(key, score, 60 * 60)
    return score


CID_KEY = "i:{}"


def get_interests(store: Store, cid):
    r = store.get(CID_KEY.format(cid))
    return json.loads(r) if r else []
