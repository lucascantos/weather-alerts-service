import time

def retry(func):
    def wrapper(*args, **kwargs):
        RETRY = 3
        while RETRY > 0:
            RETRY -=1
            response = func(*args, **kwargs)
            if not response:
                print("Retrying: "+str(RETRY))
                time.sleep(2)
            else:
                break
        if response:
            return response
        else:
            raise Exception()
    return wrapper


def timeit(func):
    def wrapper(*args, **kwargs):
        from time import time
        start = time()
        response = func(*args, **kwargs)
        print(f"Elapsed: {(time() - start):.2f}s | {((time() - start)/60):.2f}min")
        return response
    return wrapper