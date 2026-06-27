# 前端组件规范

本规范用于约束 React/Vue 等前端项目中的组件开发。

## 1. 组件命名

| 类型 | 规则 | 示例 |
|------|------|------|
| 组件文件 | PascalCase | `GoBoard.tsx` |
| 组件名 | PascalCase | `GoBoard` |
| 样式文件 | 与组件同名，`.module.css` | `GoBoard.module.css` |
| 测试文件 | `ComponentName.test.tsx` | `GoBoard.test.tsx` |
| Hook 文件 | `use` 前缀，camelCase | `useGameState.ts` |
| 工具函数 | camelCase，动词开头 | `formatMoveHistory.ts` |

## 2. React 组件规范

### 函数组件优先

```tsx
// 推荐
function GoBoard({ size, onMove }: GoBoardProps) {
  return <div className={styles.board}>{/* ... */}</div>;
}

// 不推荐 class 组件（除非需要生命周期管理）
```

### Props 类型定义

```tsx
interface GoBoardProps {
  size: number;
  onMove: (position: Position) => void;
  disabled?: boolean;
}
```

### 中文注释要求

所有组件和关键函数必须有中文注释：

```tsx
/**
 * 围棋棋盘组件
 * 支持19路/13路/9路棋盘渲染，点击落子功能
 */
function GoBoard({ size, onMove }: GoBoardProps) {
  // 处理用户点击落子事件
  const handleClick = (x: number, y: number) => {
    // 检查是否可落子
    if (isValidMove(x, y)) {
      onMove({ x, y });
    }
  };
  // ... 其他逻辑
}
```

### 状态管理

- 使用 Zustand/Redux 等全局状态管理共享状态
- 组件内部状态使用 useState
- 派生状态使用 useMemo/useCallback
- 副作用使用 useEffect

## 3. 样式规范

### CSS Modules

```tsx
// 推荐：CSS Modules
import styles from './GoBoard.module.css';
<div className={styles.board}>...</div>

// 不推荐：全局样式直接使用
import './GoBoard.css'; // 仅用于全局样式
```

### 样式组织

```
components/
  GoBoard/
    GoBoard.tsx          # 组件逻辑
    GoBoard.module.css   # 组件样式
    GoBoard.test.tsx     # 测试
    index.ts             # 导出
```

## 4. 性能优化

### 避免不必要的重渲染

```tsx
// 使用 React.memo 包装纯展示组件
const BoardCell = React.memo(({ x, y, stone }: CellProps) => {
  return <div className={styles.cell}>{stone}</div>;
});

// 使用 useMemo 缓存计算结果
const winRate = useMemo(() => calculateWinRate(gameState), [gameState]);

// 使用 useCallback 稳定回调引用
const handleMove = useCallback((pos: Position) => {
  dispatch({ type: 'MOVE', position: pos });
}, [dispatch]);
```

### 懒加载

```tsx
const AIPanel = lazy(() => import('./AIPanel'));

// 使用 Suspense 包裹
<Suspense fallback={<Loading />}>
  <AIPanel />
</Suspense>
```

## 5. 测试要求

每个组件应有对应测试：

```tsx
describe('GoBoard', () => {
  it('渲染正确数量的交叉点', () => {
    render(<GoBoard size={19} />);
    expect(screen.getAllByRole('button').length).toBe(19 * 19);
  });

  it('点击可落子位置触发 onMove', () => {
    const onMove = jest.fn();
    render(<GoBoard size={9} onMove={onMove} />);
    fireEvent.click(screen.getAllByRole('button')[0]);
    expect(onMove).toHaveBeenCalled();
  });
});
```

## 6. 提交前检查清单

- [ ] 组件有中文注释
- [ ] Props 有类型定义
- [ ] 样式使用 CSS Modules
- [ ] 不必要的重渲染已优化
- [ ] 有对应的单元测试
- [ ] 构建通过（npm run build）