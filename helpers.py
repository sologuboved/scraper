import json
import time
from functools import wraps


def which_watch(func):
    @wraps(func)
    def wrapper(*args, **kwargs):

        def report_time():
            print("\n{} took {}\n".format(func.__name__,
                                          time.strftime("%H:%M:%S", time.gmtime(time.perf_counter() - start))))

        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
        except BaseException as e:
            raise e
        else:
            return result
        finally:
            report_time()

    return wrapper


def counter(total=None, every=1):
    count = 0
    if total:
        postfix = " / {}".format(total)
    else:
        postfix = str()
    while True:
        count += 1
        if count == 1 or count == total or not count % every:
            print("\r{}{}".format(count, postfix), end=str(), flush=True)
        yield count


def load_utf_json(json_file):
    with open(json_file, encoding='utf8') as data:
        return json.load(data)


def dump_utf_json(entries, json_file):
    with open(json_file, 'w', encoding='utf-8') as handler:
        json.dump(entries, handler, ensure_ascii=False, sort_keys=True, indent=2)
