if __name__ == '__main__':
    n = int(input())
    moves = input()
    x = 0
    y = 0
    x += moves.count('R')
    x -= moves.count('L')
    y += moves.count('F')
    y -= moves.count('B')
    print(f'{x} {y}')