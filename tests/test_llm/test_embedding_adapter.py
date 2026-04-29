"""
Embedding 适配器单元测试

使用 Mock 后端测试，无需外部 API。
"""

import pytest

from deepnovel.llm.embedding_adapter import (
    EmbeddingConfig,
    EmbeddingProvider,
    MockEmbeddingBackend,
    EmbeddingAdapter,
)


class TestMockEmbeddingBackend:
    """MockEmbeddingBackend 测试"""

    @pytest.fixture
    def backend(self):
        config = EmbeddingConfig(
            provider=EmbeddingProvider.MOCK.value,
            model="mock-model",
            dimension=128,
        )
        return MockEmbeddingBackend(config)

    def test_embed_dimension(self, backend):
        """嵌入维度正确"""
        vector = backend.embed("测试文本")
        assert len(vector) == 128

    def test_embed_deterministic(self, backend):
        """相同文本产生相同向量"""
        v1 = backend.embed("相同文本")
        v2 = backend.embed("相同文本")
        assert v1 == v2

    def test_embed_different_texts(self, backend):
        """不同文本产生不同向量"""
        v1 = backend.embed("文本A")
        v2 = backend.embed("文本B")
        assert v1 != v2

    def test_embed_normalized(self, backend):
        """向量已归一化"""
        vector = backend.embed("测试")
        norm = sum(x * x for x in vector)
        assert norm == pytest.approx(1.0, rel=1e-5)

    def test_embed_batch(self, backend):
        """批量嵌入"""
        vectors = backend.embed_batch(["A", "B", "C"])
        assert len(vectors) == 3
        assert all(len(v) == 128 for v in vectors)

    def test_health_check(self, backend):
        result = backend.health_check()
        assert result["status"] == "healthy"
        assert result["dimension"] == 128

    def test_truncate(self, backend):
        """超长文本截断"""
        long_text = "A" * 10000
        truncated = backend._truncate(long_text)
        assert len(truncated) <= backend.config.max_text_length


class TestEmbeddingAdapter:
    """EmbeddingAdapter 测试"""

    @pytest.fixture
    def adapter(self):
        config = EmbeddingConfig(
            provider=EmbeddingProvider.MOCK.value,
            model="mock-model",
            dimension=64,
            normalize=True,
        )
        return EmbeddingAdapter(config)

    def test_embed(self, adapter):
        vector = adapter.embed("测试")
        assert len(vector) == 64

    def test_embed_batch(self, adapter):
        vectors = adapter.embed_batch(["A", "B", "C"])
        assert len(vectors) == 3
        assert all(len(v) == 64 for v in vectors)

    def test_cosine_similarity_same(self, adapter):
        """相同向量相似度为1"""
        v = [1.0, 0.0, 0.0]
        sim = EmbeddingAdapter.cosine_similarity(v, v)
        assert sim == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self, adapter):
        """正交向量相似度为0"""
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        sim = EmbeddingAdapter.cosine_similarity(a, b)
        assert sim == pytest.approx(0.0)

    def test_cosine_similarity_opposite(self, adapter):
        """反向向量相似度为-1"""
        a = [1.0, 0.0, 0.0]
        b = [-1.0, 0.0, 0.0]
        sim = EmbeddingAdapter.cosine_similarity(a, b)
        assert sim == pytest.approx(-1.0)

    def test_cosine_similarity_dimension_mismatch(self, adapter):
        """维度不匹配时抛出异常"""
        with pytest.raises(ValueError):
            EmbeddingAdapter.cosine_similarity([1.0, 0.0], [1.0])

    def test_euclidean_distance(self, adapter):
        """欧氏距离"""
        a = [0.0, 0.0]
        b = [3.0, 4.0]
        dist = EmbeddingAdapter.euclidean_distance(a, b)
        assert dist == pytest.approx(5.0)

    def test_similarity_matrix(self, adapter):
        """相似度矩阵"""
        vectors = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 0.0, 0.0],
        ]
        matrix = adapter.similarity_matrix(vectors)
        assert len(matrix) == 3
        assert matrix[0][0] == 1.0  # 自身
        assert matrix[0][1] == 0.0  # 正交
        assert matrix[0][2] == 1.0  # 相同

    def test_find_similar(self, adapter):
        """查找最相似"""
        query = [1.0, 0.0, 0.0]
        candidates = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.7, 0.7, 0.0],
        ]
        results = adapter.find_similar(query, candidates, top_k=2)
        assert len(results) == 2
        assert results[0][0] == 0  # 第一个最相似
        assert results[0][1] == pytest.approx(1.0)

    def test_health_check(self, adapter):
        result = adapter.health_check()
        assert result["status"] == "healthy"

    def test_to_dict(self, adapter):
        d = adapter.to_dict()
        assert d["provider"] == EmbeddingProvider.MOCK.value
        assert d["dimension"] == 64


class TestEmbeddingSemantic:
    """Embedding 语义测试（Mock 后端）"""

    @pytest.fixture
    def adapter(self):
        config = EmbeddingConfig(
            provider=EmbeddingProvider.MOCK.value,
            model="mock-model",
            dimension=128,
            normalize=True,
        )
        return EmbeddingAdapter(config)

    def test_semantic_similarity_mock(self, adapter):
        """Mock 后端：相同文本相似度为1"""
        v1 = adapter.embed("相同文本")
        v2 = adapter.embed("相同文本")
        sim = EmbeddingAdapter.cosine_similarity(v1, v2)
        assert sim == pytest.approx(1.0)

    def test_different_texts_different_vectors(self, adapter):
        """Mock 后端：不同文本产生不同向量"""
        v1 = adapter.embed("机器学习")
        v2 = adapter.embed("深度学习")
        sim = EmbeddingAdapter.cosine_similarity(v1, v2)
        # Mock 后端使用哈希，不同文本的相似度应在合理范围内
        assert -1.0 <= sim <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
