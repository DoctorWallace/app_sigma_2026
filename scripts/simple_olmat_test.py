#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.contrib.auth.models import Group
from icts.models import OLMATRequest

def test_olmat():
    print("Testing OLMAT setup...")
    
    # Test group exists
    try:
        group = Group.objects.get(name="olmat_technicians")
        print("OK: Group exists")
    except Group.DoesNotExist:
        print("ERROR: Group does not exist")
        return False
    
    # Test model
    try:
        count = OLMATRequest.objects.count()
        print(f"OK: OLMATRequest model works, count: {count}")
    except Exception as e:
        print(f"ERROR: Model error: {e}")
        return False
    
    print("OLMAT setup test completed successfully!")
    return True

if __name__ == "__main__":
    test_olmat()
