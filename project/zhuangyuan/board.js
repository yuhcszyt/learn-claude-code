export const DEFAULT_BOARD = [
  { id: "li-wenxuan", name: "李文轩" },
  { id: "wang-jingxing", name: "王景行" },
  { id: "zhao-qingyuan", name: "赵清远" },
  { id: "chen-huaijin", name: "陈怀瑾" },
  { id: "lin-zhibai", name: "林知白" },
  { id: "zhou-yunzhou", name: "周云舟" },
  { id: "shen-yanqiu", name: "沈砚秋" },
  { id: "gu-mingche", name: "顾明澈" },
  { id: "xu-changan", name: "许长安" },
  { id: "su-zijin", name: "苏子衿" },
];

export function promoteZhuangyuan(board, name, ceremonyId) {
  const winner = {
    id: `zhuangyuan-${ceremonyId}`,
    name: name.trim(),
  };

  return [winner, ...board].slice(0, 10);
}
