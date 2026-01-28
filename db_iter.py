import os
import types

from database import (
    DB_DIR,
    ADMIN_DB_PATH,
    USERS_DB_PATH,
    EXAMS_DB_PATH,
    SCORES_DB_PATH,
    CONFIG_DB_PATH,
    PROGRESS_DB_PATH,
)

from db_iter_conf import (
    simple_iter_dict
)

# 当前数据库版本，数据库更新需要更改
__current_db_version__ = "260128"
__ver_train_dict__ = {
    # 模块名: 模块版本过度标识
    simple_iter_dict.__name__: simple_iter_dict.VER_TRAIN
}


__from_iter_dict__ = "__from_iter_dict__"


ITER_VERSION_ACTION_MAP = {
    "origin": {"next_iter_ver": "260128", "action": {"func": simple_iter_dict.__simple_columns_iter__, "param": (__from_iter_dict__,)}}
}


def version_check_and_iter(db_file_version="origin"):
    if os.path.exists(os.path.join(DB_DIR, ".db_version")):
        with open(os.path.join(DB_DIR, ".db_version"), "r") as f:
            db_file_version = f.read().strip()
    if db_file_version == __current_db_version__:
        print("It's newest version")
        return db_file_version
    action = ITER_VERSION_ACTION_MAP[db_file_version]["action"]
    target_version = ITER_VERSION_ACTION_MAP[db_file_version]["next_iter_ver"]
    if __ver_train_dict__[simple_iter_dict.__name__].get("all") in ["all", target_version]:
        pass
    elif __ver_train_dict__[simple_iter_dict.__name__].get(db_file_version):
        module_target_version = __ver_train_dict__[simple_iter_dict.__name__].get(db_file_version)
        if module_target_version != target_version:
            print("Target version not match:", target_version)
            return None
    elif not __ver_train_dict__[simple_iter_dict.__name__].get(db_file_version):
        print("Current version not match:", db_file_version)
        return None
    else:
        print("Unknown error")
        return None
    if isinstance(action["func"], types.FunctionType) and isinstance(action["param"], tuple):
        if __from_iter_dict__ in action["param"]:
            action["func"](simple_iter_dict.ITER_DICT[db_file_version])
        else:
            action["func"](*action["param"])
    elif isinstance(action, list):
        for a in action:
            if isinstance(a["func"], types.FunctionType) and isinstance(a["param"], tuple):
                if __from_iter_dict__ in a["param"]:
                    a["func"](simple_iter_dict.ITER_DICT[db_file_version])
                else:
                    a["func"](*a["param"])
    print(f"Iter done: {db_file_version} ---> {target_version}")
    db_file_version = target_version
    with open(os.path.join(DB_DIR, ".db_version"), "w") as f:
        f.write(db_file_version)
    return db_file_version


def iter_loop():
    iter_version = "origin"
    can_iter = False
    iter_version_action = list(ITER_VERSION_ACTION_MAP.values())
    for iter_data in iter_version_action:
        print(iter_data.keys())
        if __current_db_version__ in iter_data["next_iter_ver"]:
            can_iter = True
            print("can_iter:", can_iter)
            break
    if can_iter:
        while iter_version != __current_db_version__:
            iter_version = version_check_and_iter(iter_version)
        return True
    else:
        return False
