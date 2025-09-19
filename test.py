import random

def quicksort(alist, left=0, right=None):
    if right is None:
        right = len(alist)-1
    if left >= right:
        return
    # pick a pivot at random
    idx = random.randint(left, right)
    pivot = alist[idx]
    # swap positions with the first element
    alist[idx], alist[left] = alist[left], alist[idx]
    # iterate through the list
    l, r = left+1, right
    while l <= r:
        if alist[l] < pivot:
            l += 1
        elif alist[r] > pivot:
            r -= 1
        else:
            alist[l], alist[r] = alist[r], alist[l]
            l += 1
            r -= 1
    alist[left], alist[l-1] = alist[l-1], alist[left]
    quicksort(alist, left, l-2)
    quicksort(alist, l, right)

def quicksort_(alist):
    if len(alist) <= 1:
        return alist
    pivot = random.choice(alist)
    left = [x for x in alist if x < pivot]
    mid = [x for x in alist if x == pivot]
    right = [x for x in alist if x > pivot]
    return quicksort_(left) + mid + quicksort_(right)

alist = []
for i in range(20):
    alist.append(random.randint(0, 100))
print(alist)
quicksort(alist)
print(alist)
print(quicksort_(alist))