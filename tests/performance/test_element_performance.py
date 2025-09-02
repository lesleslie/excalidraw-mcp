"""Performance tests for element operations."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from excalidraw_mcp.element_factory import ElementFactory


class TestElementPerformance:
    """Performance tests for element operations."""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_element_creation_performance(self, performance_monitor):
        """Test element creation performance under load."""
        factory = ElementFactory()
        element_count = 10000

        start_time = time.time()

        # Create many elements
        elements = []
        for i in range(element_count):
            element_data = {
                "type": "rectangle",
                "x": i * 10,
                "y": i * 5,
                "width": 100 + (i % 50),
                "height": 80 + (i % 30),
                "strokeColor": f"#{i % 16:06x}",
                "backgroundColor": "#ffffff",
            }
            element = factory.create_element(element_data)
            elements.append(element)

        end_time = time.time()
        duration = end_time - start_time

        # Performance assertions
        assert len(elements) == element_count
        assert duration < 5.0  # Should complete in under 5 seconds

        # Calculate rate
        elements_per_second = element_count / duration
        print(f"\nElement creation rate: {elements_per_second:.2f} elements/second")

        # Should create at least 2000 elements per second
        assert elements_per_second > 2000

    @pytest.mark.performance
    def test_element_validation_performance(self, performance_monitor):
        """Test validation performance with various inputs."""
        factory = ElementFactory()

        # Test different types of validation scenarios
        test_cases = [
            {"type": "rectangle", "x": 100, "y": 200, "width": 150, "height": 100},
            {"type": "ellipse", "x": 50, "y": 75, "width": 200, "height": 150},
            {"type": "text", "x": 0, "y": 0, "text": "Sample text", "fontSize": 16},
            {"type": "line", "x": 10, "y": 20, "width": 100, "height": 0},
            {"type": "arrow", "x": 25, "y": 50, "width": 75, "height": 25},
        ]

        iterations = 1000
        start_time = time.time()

        for _ in range(iterations):
            for test_case in test_cases:
                factory.validate_element_data(test_case.copy())

        end_time = time.time()
        duration = end_time - start_time

        total_validations = iterations * len(test_cases)
        validations_per_second = total_validations / duration

        print(f"\nValidation rate: {validations_per_second:.2f} validations/second")

        # Should validate at least 10000 per second
        assert validations_per_second > 10000
        assert duration < 2.0  # Should complete in under 2 seconds

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_element_operations(self, performance_monitor):
        """Test performance under concurrent operations."""
        factory = ElementFactory()

        async def create_elements_batch(batch_id: int, batch_size: int = 100):
            """Create a batch of elements."""
            elements = []
            for i in range(batch_size):
                element_data = {
                    "type": "rectangle",
                    "x": batch_id * 1000 + i * 10,
                    "y": i * 5,
                    "width": 100,
                    "height": 80,
                }
                element = factory.create_element(element_data)
                elements.append(element)
            return elements

        # Create 10 concurrent batches
        batch_count = 10
        batch_size = 100

        start_time = time.time()

        tasks = []
        for batch_id in range(batch_count):
            task = create_elements_batch(batch_id, batch_size)
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        end_time = time.time()
        duration = end_time - start_time

        # Verify results
        total_elements = sum(len(batch) for batch in results)
        expected_total = batch_count * batch_size

        assert total_elements == expected_total

        elements_per_second = total_elements / duration
        print(f"\nConcurrent creation rate: {elements_per_second:.2f} elements/second")

        # Concurrent operations should be reasonably fast
        assert elements_per_second > 1000
        assert duration < 3.0

    @pytest.mark.performance
    def test_memory_usage_element_creation(self, performance_monitor):
        """Test memory usage during element creation."""
        import gc

        import psutil

        factory = ElementFactory()
        process = psutil.Process()

        # Get baseline memory usage
        gc.collect()  # Force garbage collection
        baseline_memory = process.memory_info().rss

        # Create elements
        elements = []
        element_count = 5000

        for i in range(element_count):
            element_data = {
                "type": "rectangle",
                "x": i,
                "y": i * 2,
                "width": 100,
                "height": 80,
                "text": f"Element {i}" if i % 10 == 0 else None,  # Some text elements
            }
            element = factory.create_element(element_data)
            elements.append(element)

            # Check memory every 1000 elements
            if i % 1000 == 0 and i > 0:
                current_memory = process.memory_info().rss
                memory_growth = current_memory - baseline_memory
                memory_per_element = memory_growth / i

                # Memory per element should be reasonable (under 1KB each)
                assert memory_per_element < 1024, (
                    f"Memory per element too high: {memory_per_element:.2f} bytes"
                )

        # Final memory check
        final_memory = process.memory_info().rss
        total_memory_growth = final_memory - baseline_memory
        memory_per_element = total_memory_growth / element_count

        print(f"\nMemory usage per element: {memory_per_element:.2f} bytes")
        print(f"Total memory growth: {total_memory_growth / 1024 / 1024:.2f} MB")

        # Should use less than 512 bytes per element on average
        assert memory_per_element < 512

    @pytest.mark.performance
    def test_validation_error_performance(
        self, performance_monitor, security_test_data
    ):
        """Test performance when handling validation errors."""
        factory = ElementFactory()

        # Test cases that should fail validation
        invalid_cases = [
            {"type": "invalid_type", "x": 100, "y": 200},
            {"type": "rectangle", "x": "not_a_number", "y": 200},
            {"type": "rectangle", "x": 100, "y": 200, "width": -50},
            {"type": "rectangle", "x": 100, "y": 200, "strokeColor": "invalid_color"},
            {
                "type": "rectangle",
                "x": 100,
                "y": 200,
                "strokeWidth": 100,
            },  # Out of range
            {"x": 100, "y": 200},  # Missing type
        ]

        iterations = 1000
        start_time = time.time()

        error_count = 0
        for _ in range(iterations):
            for invalid_case in invalid_cases:
                try:
                    factory.validate_element_data(invalid_case.copy())
                except ValueError:
                    error_count += 1

        end_time = time.time()
        duration = end_time - start_time

        total_attempts = iterations * len(invalid_cases)
        validations_per_second = total_attempts / duration

        print(
            f"\nError validation rate: {validations_per_second:.2f} validations/second"
        )
        print(f"Error detection rate: {error_count / total_attempts * 100:.1f}%")

        # Should handle errors quickly
        assert validations_per_second > 5000
        assert duration < 2.0

        # Should catch most/all validation errors
        assert error_count >= total_attempts * 0.9  # At least 90% should be caught

    @pytest.mark.performance
    def test_large_text_element_performance(
        self, performance_monitor, security_test_data
    ):
        """Test performance with large text elements."""
        factory = ElementFactory()

        # Create elements with increasingly large text
        text_sizes = [100, 1000, 10000, 50000]  # Character counts

        for text_size in text_sizes:
            large_text = "A" * text_size

            element_data = {
                "type": "text",
                "x": 100,
                "y": 200,
                "text": large_text,
                "fontSize": 16,
            }

            start_time = time.time()
            element = factory.create_element(element_data)
            end_time = time.time()

            duration = end_time - start_time

            print(f"\nText size {text_size}: {duration:.4f}s")

            # Should handle even large text quickly (under 0.1 seconds)
            assert duration < 0.1
            assert element["text"] == large_text
            assert len(element["text"]) == text_size

    @pytest.mark.performance
    def test_element_update_preparation_performance(self, performance_monitor):
        """Test performance of update data preparation."""
        factory = ElementFactory()

        # Prepare various update scenarios
        update_scenarios = [
            {"id": "test-123", "x": 150, "y": 250},
            {"id": "test-456", "strokeColor": "#ff0000", "backgroundColor": "#00ff00"},
            {"id": "test-789", "width": 200, "height": 150, "opacity": 75},
            {
                "id": "test-abc",
                "text": "Updated text",
                "fontSize": 20,
                "fontFamily": "Arial",
            },
            {"id": "test-def", "strokeWidth": 3, "roughness": 2, "locked": True},
        ]

        iterations = 2000
        start_time = time.time()

        for _ in range(iterations):
            for scenario in update_scenarios:
                result = factory.prepare_update_data(scenario.copy())
                assert "id" in result
                assert "updatedAt" in result

        end_time = time.time()
        duration = end_time - start_time

        total_operations = iterations * len(update_scenarios)
        operations_per_second = total_operations / duration

        print(
            f"\nUpdate preparation rate: {operations_per_second:.2f} operations/second"
        )

        # Should handle update preparation quickly
        assert operations_per_second > 5000
        assert duration < 2.0

    @pytest.mark.performance
    def test_thread_safety_performance(self, performance_monitor):
        """Test performance under multi-threaded access."""
        factory = ElementFactory()

        def create_elements_in_thread(thread_id: int, element_count: int = 100):
            """Create elements in a separate thread."""
            elements = []
            for i in range(element_count):
                element_data = {
                    "type": "rectangle",
                    "x": thread_id * 1000 + i,
                    "y": i,
                    "width": 100,
                    "height": 80,
                }
                element = factory.create_element(element_data)
                elements.append(element)
            return elements

        thread_count = 4
        elements_per_thread = 250

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = []
            for thread_id in range(thread_count):
                future = executor.submit(
                    create_elements_in_thread, thread_id, elements_per_thread
                )
                futures.append(future)

            results = [future.result() for future in futures]

        end_time = time.time()
        duration = end_time - start_time

        # Verify results
        total_elements = sum(len(batch) for batch in results)
        expected_total = thread_count * elements_per_thread

        assert total_elements == expected_total

        elements_per_second = total_elements / duration
        print(
            f"\nMulti-threaded creation rate: {elements_per_second:.2f} elements/second"
        )

        # Multi-threaded operations should be reasonably fast
        assert elements_per_second > 800  # Slightly lower due to thread overhead
        assert duration < 5.0
