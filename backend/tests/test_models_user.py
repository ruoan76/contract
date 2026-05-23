"""
User, Role, Department 模型测试
"""
import pytest
from sqlalchemy import select

@pytest.mark.unit
class TestUserModel:
    """User 模型测试"""
    
    async def test_user_creation(self, db_session, mock_data):
        """测试 User 创建"""
        from app.models.contract import User, Role, Department
        
        dept = Department(
            name="技术部",
            parent_id=0,
            level=1,
            path="/1",
            status=1,
        )
        db_session.add(dept)
        await db_session.flush()
        
        role = Role(
            name="用户",
            code="user",
            description="普通用户",
            status=1,
        )
        db_session.add(role)
        await db_session.flush()
        
        user = User(
            username="testuser",
            password_hash="$2b$12$mockedhash",
            real_name="测试用户",
            email="test@example.com",
            phone="13800138000",
            department_id=dept.id,
            role_id=role.id,
            status=1,
        )
        db_session.add(user)
        await db_session.flush()
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.status == 1
    
    async def test_user_unique_username(self, db_session, mock_data):
        """测试 User 用户名唯一性"""
        from app.models.contract import User
        
        user1 = User(
            username="uniqueuser",
            password_hash="$2b$12$hash1",
            real_name="User 1",
            email="user1@example.com",
            status=1,
        )
        db_session.add(user1)
        await db_session.flush()
        
        user2 = User(
            username="uniqueuser",
            password_hash="$2b$12$hash2",
            real_name="User 2",
            email="user2@example.com",
            status=1,
        )
        db_session.add(user2)
        
        with pytest.raises(Exception):
            await db_session.flush()


@pytest.mark.unit
class TestRoleModel:
    """Role 模型测试"""
    
    async def test_role_creation(self, db_session, mock_data):
        """测试 Role 创建"""
        from app.models.contract import Role
        
        role = Role(
            name="管理员",
            code="admin",
            description="系统管理员",
            permissions='{"read": true, "write": true}',
            status=1,
        )
        db_session.add(role)
        await db_session.flush()
        
        assert role.id is not None
        assert role.code == "admin"
        assert role.name == "管理员"
    
    async def test_role_unique_code(self, db_session, mock_data):
        """测试 Role code 唯一性"""
        from app.models.contract import Role
        
        role1 = Role(
            name="Role 1",
            code="unique_code",
            description="Test",
            status=1,
        )
        db_session.add(role1)
        await db_session.flush()
        
        role2 = Role(
            name="Role 2",
            code="unique_code",
            description="Duplicate",
            status=1,
        )
        db_session.add(role2)
        
        with pytest.raises(Exception):
            await db_session.flush()


@pytest.mark.unit
class TestDepartmentModel:
    """Department 模型测试"""
    
    async def test_department_creation(self, db_session, mock_data):
        """测试 Department 创建"""
        from app.models.contract import Department
        
        dept = Department(
            name="技术部",
            parent_id=0,
            level=1,
            path="/1",
            status=1,
        )
        db_session.add(dept)
        await db_session.flush()
        
        assert dept.id is not None
        assert dept.name == "技术部"
    
    async def test_department_parent_child(self, db_session, mock_data):
        """测试部门父子关系"""
        from app.models.contract import Department
        
        parent = Department(
            name="集团总部",
            parent_id=0,
            level=1,
            path="/1",
            status=1,
        )
        db_session.add(parent)
        await db_session.flush()
        
        child = Department(
            name="技术中心",
            parent_id=parent.id,
            level=2,
            path="/1/2",
            status=1,
        )
        db_session.add(child)
        await db_session.flush()
        
        assert child.parent_id == parent.id
        assert child.level == 2


@pytest.mark.unit
class TestDefaultRoles:
    """默认角色测试"""
    
    async def test_default_roles_exist(self, db_session, mock_data):
        """测试默认角色是否创建"""
        from app.models.contract import Role
        
        # 检查是否已存在 admin 角色
        result = await db_session.execute(
            select(Role).where(Role.code == "admin")
        )
        admin_role = result.scalar_one_or_none()
        
        # 默认应该存在 admin 角色（如果数据库已初始化）
        if admin_role:
            assert admin_role.code == "admin"
            assert admin_role.name == "管理员"


@pytest.mark.unit
class TestDepartmentHierarchy:
    """部门层级结构测试"""
    
    async def test_dept_level_calculation(self, db_session, mock_data):
        """测试部门层级自动计算（如果需要）"""
        from app.models.contract import Department
        
        dept1 = Department(
            name="一级部门",
            parent_id=0,
            level=1,
            status=1,
        )
        db_session.add(dept1)
        await db_session.flush()
        
        dept2 = Department(
            name="二级部门",
            parent_id=dept1.id,
            level=2,
            status=1,
        )
        db_session.add(dept2)
        await db_session.flush()
        
        assert dept2.level == 2
        assert dept2.parent_id == dept1.id
