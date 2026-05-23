# 合同审批管理平台 - 测试套件

本测试套件为合同审批管理平台后端提供完整的 pytest 测试。

## 运行测试

```bash
cd backend
pytest --tb=short -q
```

### 运行特定测试

```bash
# 运行单个测试文件
pytest tests/test_models_contract.py -v

# 运行特定测试类
pytest tests/test_services_contract.py::TestCreateContract -v

# 运行标记的测试
pytest -m "unit" -v

# 关联测试（带详细输出）
pytest -v --tb=long
```

### 运行慢测试

```bash
pytest --runslow -v
```

### 运行集成测试

```bash
pytest --runintegration -v
```

## 项目结构

```
backend/tests/
├── conftest.py          # 全局 fixture 和配置
├── pytest.ini           # pytest 配置
├── __init__.py
├── test_models_contract.py   # ORM 模型测试
├── test_models_user.py   # 用户/角色/部门模型测试
├── test_services_contract.py # 合同服务测试
├── test_services_approval.py # 审批流程服务测试
├── test_services_archive.py  # 归档服务测试
├── test_services_seal.py     # 用印服务测试
├── test_services_audit.py    # 审计服务测试
├── test_core_security.py     # JWT/密码认证测试
├── test_api_contracts.py     # 合同 API 端点测试
├── test_middleware_auth.py   # 认证中间件测试
├── test_services_ai_review_engine.py  # AI审查引擎测试
└── example_test.py           # 示例测试文件
```

## 测试类型

- **单元测试 (unit)**: 测试单个函数/类，不依赖外部服务
- **集成测试 (integration)**: 测试多个组件集成，可能依赖数据库

标记使用:
- `@pytest.mark.unit` - 单元测试
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.slow` - 慢测试
- `@pytest.mark.apikey` - 需要 API key 的测试

## Mock 对象

测试中使用了多种 Mock 对象:
- `db_session` - 测试数据库会话
- `mock_data` - 数据工厂
- `mock_openai_client` - OpenAI 客户端 Mock
- `mock_auth_headers` - 认证请求头生成器

## 常见错误

### ImportError: No module named 'app'
确保在 `backend` 目录下运行测试

### ModuleNotFoundError: No module named 'aiosqlite'
```bash
pip install aiosqlite
```

### Database Connection Error
测试使用内存 SQLite 数据库，无需真实数据库连接。

## 添加新测试

1. 创建测试文件 `test_<module>.py`
2. 导入必要的 fixture
3. 编写测试类和方法
4. 使用 `@pytest.mark.unit` 标记测试
5. 运行 `pytest -v` 验证测试

## 代码覆盖率

```bash
pytest --cov=app --cov-report=html -v
```

生成的覆盖率报告在 `htmlcov/index.html`
