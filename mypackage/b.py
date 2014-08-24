import mypackage.a
from mypackage.a import query_database as query_database_alternate_name
from mypackage.a import query_database



def triple_database():
    return query_database() * 3

def triple_database_direct_call():
    return mypackage.a.query_database() * 3

def triple_database_alternate_name():
    return query_database_alternate_name() * 3

def triple_database_local_import():
    from mypackage.a import query_database
    return query_database() * 3
