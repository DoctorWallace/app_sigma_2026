import importlib.util as u
apps = ["portal","icts","dtf","labtemp","accounts"]
print({a: (u.find_spec(a) is not None) for a in apps})