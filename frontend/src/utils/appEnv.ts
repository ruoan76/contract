/** 开发演示：跳过登录页，自动种子账号登录 */
export const isSkipAuth = import.meta.env.VITE_SKIP_AUTH === '1'

/** 演示导航：侧栏展示全部菜单（无权限项灰显）；关闭则正式环境仅显示有权限项 */
export const isDemoNav = isSkipAuth || import.meta.env.VITE_DEMO_NAV === '1'
