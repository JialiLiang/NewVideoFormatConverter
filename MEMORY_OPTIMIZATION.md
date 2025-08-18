# Memory Optimization Guide for Render.com

## 🚨 Memory Issues Fixed

This document outlines the optimizations implemented to prevent "Ran out of memory (used over 2GB)" errors on Render.com.

## ✅ Optimizations Applied

### 1. **Reduced Concurrent Processing**
- **Before**: Up to 4 videos processed simultaneously
- **After**: Maximum 2 concurrent video processes
- **Impact**: ~50% reduction in peak memory usage

### 2. **Aggressive Memory Cleanup**
- Added garbage collection before/after each video processing
- Implemented memory monitoring with automatic cleanup at 1.5GB
- Force cleanup on errors to prevent memory leaks

### 3. **File Size Limits**
- **Before**: 500MB max file size
- **After**: 200MB max file size
- **Impact**: Reduces peak memory usage significantly

### 4. **Memory Monitoring**
- Real-time memory usage tracking
- Automatic cleanup when memory exceeds 1.5GB
- Detailed logging for debugging memory issues

### 5. **Render.com Configuration**
- Added memory optimization environment variables
- Enabled disk space allocation (2GB)
- Configured Python memory management

## 🔧 Technical Implementation

### Memory Monitoring Functions
```python
def get_memory_usage():
    """Get current memory usage in MB"""
    
def check_memory_and_cleanup():
    """Check memory usage and force cleanup if needed"""
    
def log_memory_usage(context=""):
    """Log current memory usage"""
```

### Processing Optimizations
- Reduced `max_workers` from 4 to 2 in ThreadPoolExecutor
- Added `gc.collect()` calls before/after video processing
- Memory checks after each video completion

### Configuration Changes
- `MAX_CONTENT_LENGTH`: 500MB → 200MB
- Added `psutil` for memory monitoring
- Optimized Render.com environment variables

## 📊 Expected Results

### Memory Usage Reduction
- **Peak Usage**: ~50% reduction
- **Concurrent Load**: Safer processing limits
- **Cleanup**: Automatic memory management

### File Processing
- **Smaller Files**: Better memory efficiency
- **Quality**: Same output quality maintained
- **Speed**: Slightly slower but more reliable

## 🚀 Deployment Notes

### Requirements Updated
- Added `psutil>=5.9.0` for memory monitoring
- All other dependencies remain the same

### Render.com Settings
```yaml
envVars:
  - key: PYTHONUNBUFFERED
    value: 1
  - key: MALLOC_TRIM_THRESHOLD_
    value: 100000
disk: 
  sizeGB: 2
```

## 🔍 Monitoring

### Log Messages to Watch
- `Memory usage before processing: X.XMB`
- `High memory usage detected: X.XMB - forcing cleanup`
- `Memory usage after processing: X.XMB`

### Warning Signs
- Memory usage consistently above 1.5GB
- Frequent cleanup triggers
- Processing timeouts or failures

## 🆘 If Issues Persist

### Option 1: Upgrade Render Plan
- Consider upgrading to **Standard** plan (4GB RAM)
- More expensive but handles larger files

### Option 2: Further Optimizations
- Reduce file size limit to 100MB
- Process only 1 video at a time (`max_workers=1`)
- Optimize video processing pipeline

### Option 3: External Processing
- Move video processing to separate service
- Use cloud storage for file handling
- Implement queue-based processing

## 📈 Performance vs Memory Trade-offs

| Setting | Memory Usage | Processing Speed | Reliability |
|---------|-------------|------------------|-------------|
| 4 concurrent + 500MB | High | Fast | Low |
| 2 concurrent + 200MB | Medium | Medium | High |
| 1 concurrent + 100MB | Low | Slow | Very High |

**Current Setting**: 2 concurrent + 200MB (balanced approach)
