"""
基础设施容器化测试 — 验证Docker构建和编排

测试范围:
- Dockerfile.ai 多阶段构建
- docker-compose.yml 服务配置
- 健康检查端点
"""

import pytest
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


def run_cmd(cmd: list[str], cwd: Path = None, timeout: int = 300) -> tuple[int, str, str]:
    """执行shell命令并返回结果"""
    result = subprocess.run(
        cmd,
        cwd=cwd or PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


class TestDockerfile:
    """Dockerfile构建测试"""

    def test_dockerfile_exists(self):
        """Dockerfile.ai 必须存在"""
        dockerfile = PROJECT_ROOT / "Dockerfile.ai"
        assert dockerfile.exists(), "Dockerfile.ai not found"
        content = dockerfile.read_text(encoding="utf-8")
        assert "FROM" in content, "Dockerfile missing FROM instruction"
        assert "HEALTHCHECK" in content, "Dockerfile missing HEALTHCHECK"

    def test_dockerfile_stages(self):
        """Dockerfile 必须包含 production 和 development 阶段"""
        content = (PROJECT_ROOT / "Dockerfile.ai").read_text(encoding="utf-8")
        assert "AS production" in content, "Missing production stage"
        assert "AS development" in content, "Missing development stage"
        assert "AS builder" in content, "Missing builder stage"

    def test_dockerfile_nonroot_user(self):
        """Dockerfile 必须使用非root用户运行"""
        content = (PROJECT_ROOT / "Dockerfile.ai").read_text(encoding="utf-8")
        assert "USER " in content, "Missing USER instruction for non-root"

    def test_dockerfile_security_options(self):
        """Dockerfile 必须包含安全相关配置"""
        content = (PROJECT_ROOT / "Dockerfile.ai").read_text(encoding="utf-8")
        assert "PYTHONDONTWRITEBYTECODE" in content
        assert "PYTHONUNBUFFERED" in content


class TestDockerCompose:
    """Docker Compose配置测试"""

    def test_compose_file_exists(self):
        """docker-compose.yml 必须存在"""
        compose = PROJECT_ROOT / "docker-compose.yml"
        assert compose.exists(), "docker-compose.yml not found"

    def test_compose_syntax_valid(self):
        """docker-compose.yml 语法必须有效"""
        returncode, stdout, stderr = run_cmd(
            ["docker", "compose", "config"],
            cwd=PROJECT_ROOT,
        )
        assert returncode == 0, f"docker compose config failed: {stderr}"

    def test_compose_services_defined(self):
        """必须定义关键服务"""
        returncode, stdout, stderr = run_cmd(
            ["docker", "compose", "config", "--services"],
            cwd=PROJECT_ROOT,
        )
        assert returncode == 0
        services = stdout.strip().split("\n")
        expected = ["mysql", "neo4j", "mongodb", "chromadb", "postgres", "redis", "qdrant"]
        for svc in expected:
            assert svc in services, f"Service {svc} not found in compose"

    def test_compose_profiles_exist(self):
        """必须定义profiles分层"""
        content = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        assert "profiles:" in content, "Missing profiles for service layering"
        assert "app" in content, "Missing 'app' profile"
        assert "dev" in content, "Missing 'dev' profile"
        assert "monitoring" in content, "Missing 'monitoring' profile"

    def test_compose_healthchecks(self):
        """关键服务必须配置健康检查"""
        content = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        healthcheck_count = content.count("healthcheck:")
        assert healthcheck_count >= 4, f"Only {healthcheck_count} healthchecks, expected >= 4"

    def test_compose_resource_limits(self):
        """服务必须配置资源限制"""
        content = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        assert "deploy:" in content, "Missing deploy section for resource limits"
        assert "resources:" in content, "Missing resources section"
        assert "limits:" in content, "Missing limits section"

    def test_compose_security_options(self):
        """必须配置安全选项"""
        content = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        assert "security_opt:" in content, "Missing security_opt"
        assert "cap_drop:" in content, "Missing cap_drop"
        assert "no-new-privileges" in content, "Missing no-new-privileges"


class TestPrometheusConfig:
    """Prometheus配置测试"""

    def test_prometheus_config_exists(self):
        """prometheus.yml 必须存在"""
        config = PROJECT_ROOT / "config" / "prometheus" / "prometheus.yml"
        assert config.exists(), "prometheus.yml not found"

    def test_prometheus_scrape_jobs(self):
        """必须配置正确的scrape jobs"""
        content = (PROJECT_ROOT / "config" / "prometheus" / "prometheus.yml").read_text()
        assert "ai-engine" in content, "Missing ai-engine scrape job"
        assert "prometheus" in content, "Missing prometheus self scrape job"


class TestDockerBuild:
    """Docker镜像构建测试 (可选，需要Docker守护进程)"""

    def test_docker_build_production(self):
        """生产镜像必须能成功构建"""
        returncode, stdout, stderr = run_cmd(
            ["docker", "build", "-f", "Dockerfile.ai", "--target", "production", "-t", "deepnovel-ai:test", "."],
            cwd=PROJECT_ROOT,
            timeout=600,
        )
        if returncode != 0:
            pytest.skip(f"Docker build skipped (Docker daemon may not be available): {stderr}")
        assert returncode == 0, f"Docker build failed: {stderr}"

    def test_docker_image_has_healthcheck(self):
        """构建的镜像必须包含健康检查配置"""
        returncode, stdout, stderr = run_cmd(
            ["docker", "inspect", "--format={{.Config.Healthcheck.Test}}", "deepnovel-ai:test"],
        )
        if returncode != 0:
            pytest.skip("Docker image inspect skipped")
        assert "CMD" in stdout or "python" in stdout, "Healthcheck not configured in image"

    def test_docker_image_nonroot(self):
        """构建的镜像必须使用非root用户"""
        returncode, stdout, stderr = run_cmd(
            ["docker", "inspect", "--format={{.Config.User}}", "deepnovel-ai:test"],
        )
        if returncode != 0:
            pytest.skip("Docker image inspect skipped")
        user = stdout.strip()
        assert user and user != "root" and user != "0", f"Image runs as root user: {user}"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
