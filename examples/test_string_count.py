if __name__ == "__main__":
    n = int(input())
    moves = input()
    x = 0
    y = 0
    for move in moves:
        if move == 'R':
            x += 1
        elif move == 'L':
            x -= 1
        elif move == 'F':
            y += 1
        elif move == 'B':
            y -= 1
    print(f"{x} {y}")
