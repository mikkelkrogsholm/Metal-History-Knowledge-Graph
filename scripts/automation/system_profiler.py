#!/usr/bin/env python3
"""
System profiler for dynamic resource allocation.
Detects hardware capabilities and recommends optimal settings.
"""

import os
import platform
import psutil
import multiprocessing
from typing import Dict, Any
import json


class SystemProfiler:
    """Profile system capabilities and recommend settings."""
    
    def __init__(self):
        self.profile = self._gather_system_info()
        
    def _gather_system_info(self) -> Dict[str, Any]:
        """Gather comprehensive system information."""
        # CPU information
        cpu_count = multiprocessing.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        # Memory information
        memory = psutil.virtual_memory()
        
        # Platform information
        system = platform.system()
        machine = platform.machine()
        
        # Check if running on Apple Silicon
        is_apple_silicon = (system == 'Darwin' and machine == 'arm64')
        
        return {
            'system': {
                'platform': system,
                'machine': machine,
                'processor': platform.processor(),
                'is_apple_silicon': is_apple_silicon
            },
            'cpu': {
                'physical_cores': psutil.cpu_count(logical=False),
                'logical_cores': cpu_count,
                'frequency_mhz': cpu_freq.current if cpu_freq else None,
                'usage_percent': psutil.cpu_percent(interval=1)
            },
            'memory': {
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'used_percent': memory.percent
            },
            'performance_tier': self._determine_performance_tier(
                cpu_count, memory.total, is_apple_silicon
            )
        }
    
    def _determine_performance_tier(self, cores: int, memory_bytes: int, 
                                   is_apple_silicon: bool) -> str:
        """Determine system performance tier."""
        memory_gb = memory_bytes / (1024**3)
        
        # Apple Silicon gets a boost due to unified memory and efficiency
        if is_apple_silicon:
            if cores >= 10 and memory_gb >= 32:
                return 'high'
            elif cores >= 8 and memory_gb >= 16:
                return 'medium-high'
            elif cores >= 8 and memory_gb >= 8:
                return 'medium'
            else:
                return 'low'
        else:
            # Regular x86/x64 systems
            if cores >= 16 and memory_gb >= 32:
                return 'high'
            elif cores >= 8 and memory_gb >= 16:
                return 'medium-high'
            elif cores >= 4 and memory_gb >= 8:
                return 'medium'
            else:
                return 'low'
    
    def get_extraction_settings(self) -> Dict[str, Any]:
        """Get recommended extraction settings based on system profile."""
        tier = self.profile['performance_tier']
        cores = self.profile['cpu']['physical_cores']
        memory_gb = self.profile['memory']['available_gb']
        
        # Base settings for different tiers
        settings = {
            'high': {
                'parallel_workers': min(cores - 1, 8),  # Leave 1 core free, max 8
                'batch_size': 10,
                'num_ctx': 16384,
                'num_predict': 4096,
                'num_threads': 4,  # Threads per Ollama instance
                'prefetch_chunks': True,
                'use_memory_cache': True
            },
            'medium-high': {
                'parallel_workers': min(cores - 1, 4),
                'batch_size': 5,
                'num_ctx': 16384,
                'num_predict': 4096,
                'num_threads': 2,
                'prefetch_chunks': True,
                'use_memory_cache': True
            },
            'medium': {
                'parallel_workers': min(max(cores - 1, 2), 3),
                'batch_size': 3,
                'num_ctx': 8192,
                'num_predict': 2048,
                'num_threads': 2,
                'prefetch_chunks': False,
                'use_memory_cache': memory_gb > 4
            },
            'low': {
                'parallel_workers': 1,
                'batch_size': 1,
                'num_ctx': 8192,
                'num_predict': 2048,
                'num_threads': 1,
                'prefetch_chunks': False,
                'use_memory_cache': False
            }
        }
        
        # Get tier settings
        tier_settings = settings.get(tier, settings['medium'])
        
        # Adjust for available memory
        if memory_gb < 4:
            tier_settings['parallel_workers'] = 1
            tier_settings['use_memory_cache'] = False
        elif memory_gb < 8:
            tier_settings['parallel_workers'] = min(tier_settings['parallel_workers'], 2)
        
        # Add system info to settings
        tier_settings['system_profile'] = {
            'tier': tier,
            'cores': cores,
            'memory_gb': round(memory_gb, 2),
            'is_apple_silicon': self.profile['system']['is_apple_silicon']
        }
        
        return tier_settings
    
    def get_resource_limits(self) -> Dict[str, Any]:
        """Get resource limits to prevent system overload."""
        memory_gb = self.profile['memory']['total_gb']
        
        return {
            'max_memory_percent': 75,  # Don't use more than 75% of RAM
            'max_cpu_percent': 85,     # Leave some CPU for system
            'memory_per_worker_gb': max(1.5, memory_gb * 0.15),  # 15% per worker
            'monitor_resources': True,
            'throttle_on_high_usage': True
        }
    
    def print_profile(self):
        """Print system profile in a readable format."""
        print("\n🖥️  System Profile")
        print("=" * 50)
        
        # System info
        print(f"Platform: {self.profile['system']['platform']} ({self.profile['system']['machine']})")
        if self.profile['system']['is_apple_silicon']:
            print("✨ Apple Silicon detected - optimized performance available")
        
        # CPU info
        cpu = self.profile['cpu']
        print(f"\nCPU:")
        print(f"  Physical cores: {cpu['physical_cores']}")
        print(f"  Logical cores: {cpu['logical_cores']}")
        if cpu['frequency_mhz']:
            print(f"  Frequency: {cpu['frequency_mhz']} MHz")
        print(f"  Current usage: {cpu['usage_percent']}%")
        
        # Memory info
        mem = self.profile['memory']
        print(f"\nMemory:")
        print(f"  Total: {mem['total_gb']} GB")
        print(f"  Available: {mem['available_gb']} GB")
        print(f"  Used: {mem['used_percent']}%")
        
        # Performance tier
        print(f"\nPerformance Tier: {self.profile['performance_tier'].upper()}")
        print("=" * 50)
    
    def save_profile(self, path: str = 'system_profile.json'):
        """Save system profile to file."""
        with open(path, 'w') as f:
            json.dump({
                'profile': self.profile,
                'extraction_settings': self.get_extraction_settings(),
                'resource_limits': self.get_resource_limits()
            }, f, indent=2)
        print(f"\nProfile saved to: {path}")


def main():
    """Test system profiler."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Profile system for optimal settings")
    parser.add_argument('--save', action='store_true', help='Save profile to file')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    profiler = SystemProfiler()
    
    if args.json:
        print(json.dumps({
            'profile': profiler.profile,
            'extraction_settings': profiler.get_extraction_settings(),
            'resource_limits': profiler.get_resource_limits()
        }, indent=2))
    else:
        profiler.print_profile()
        
        # Show recommended settings
        settings = profiler.get_extraction_settings()
        print("\n🚀 Recommended Extraction Settings")
        print("=" * 50)
        print(f"Parallel workers: {settings['parallel_workers']}")
        print(f"Batch size: {settings['batch_size']}")
        print(f"Context window: {settings['num_ctx']}")
        print(f"Memory cache: {'Enabled' if settings['use_memory_cache'] else 'Disabled'}")
        print(f"Prefetch: {'Enabled' if settings['prefetch_chunks'] else 'Disabled'}")
        
        # Show limits
        limits = profiler.get_resource_limits()
        print(f"\nResource Limits:")
        print(f"  Max memory: {limits['max_memory_percent']}%")
        print(f"  Max CPU: {limits['max_cpu_percent']}%")
        print(f"  Memory per worker: {limits['memory_per_worker_gb']} GB")
        
    if args.save:
        profiler.save_profile()


if __name__ == "__main__":
    main()