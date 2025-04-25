from collections import deque

def max_candies_in_shortest_path(grid, start, end):
    """
    计算妈妈在最短时间内到达宝宝位置能获得的最大糖果数

    参数:
        grid: 二维矩阵，0表示障碍物，正整数表示糖果数量
        start: 妈妈位置 (row, col)
        end: 宝宝位置 (row, col)

    返回:
        (最短时间, 最大糖果数) 元组，如果无法到达返回 (-1, -1)
    """
    if not grid or not grid[0]:
        return (-1, -1)

    rows, cols = len(grid), len(grid[0])
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # 上下左右

    # 检查起点或终点是否有效
    if (start[0] < 0 or start[0] >= rows or start[1] < 0 or start[1] >= cols or
        end[0] < 0 or end[0] >= rows or end[1] < 0 or end[1] >= cols):
        return (-1, -1)

    if grid[start[0]][start[1]] == 0 or grid[end[0]][end[1]] == 0:
        return (-1, -1)  # 起点或终点是障碍物

    # 初始化距离和糖果矩阵
    dist = [[-1 for _ in range(cols)] for _ in range(rows)]
    candies = [[0 for _ in range(cols)] for _ in range(rows)]

    q = deque()
    q.append(start)
    dist[start[0]][start[1]] = 0
    candies[start[0]][start[1]] = grid[start[0]][start[1]]

    while q:
        x, y = q.popleft()

        # 如果到达终点，不需要继续处理
        if (x, y) == end:
            continue

        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < rows and 0 <= ny < cols and grid[nx][ny] != 0:
                new_dist = dist[x][y] + 1
                new_candies = candies[x][y] + grid[nx][ny]

                # 如果是首次访问或者找到更优解
                if dist[nx][ny] == -1 or new_dist < dist[nx][ny]:
                    dist[nx][ny] = new_dist
                    candies[nx][ny] = new_candies
                    q.append((nx, ny))
                elif new_dist == dist[nx][ny] and new_candies > candies[nx][ny]:
                    # 相同距离但更多糖果
                    candies[nx][ny] = new_candies
                    # 需要重新处理这个节点以传播新的糖果值
                    q.append((nx, ny))

    return (dist[end[0]][end[1]], candies[end[0]][end[1]]) if dist[end[0]][end[1]] != -1 else (-1, -1)

# 示例用法
if __name__ == "__main__":
    # 示例地图
    grid = [
        [1, 2, 3],
        [0, 5, 0],  # 0表示障碍物
        [7, 8, 9]
    ]
    start = (0, 0)  # 妈妈位置
    end = (2, 2)     # 宝宝位置

    time, candies = max_candies_in_shortest_path(grid, start, end)
    print(f"最短时间: {time}, 最多糖果: {candies}")
