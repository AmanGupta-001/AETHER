import os
import subprocess
import shutil
import psutil
from langchain_core.tools import tool
from langchain_core.tools.structured import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional

class SystemMonitorInput(BaseModel):
    category: Optional[str] = Field(
        default="all",
        description="The component to check: 'all', 'cpu', 'ram', 'gpu', 'storage', or 'battery'."
    )

def _get_gpu_info():
    """Query NVIDIA GPU metrics via nvidia-smi if available."""
    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=name,temperature.gpu,utilization.gpu,utilization.memory,memory.total,memory.used,memory.free",
            "--format=csv,noheader,nounits"
        ]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=3).strip()
        if not output:
            return None
        
        parts = [p.strip() for p in output.split(",")]
        if len(parts) >= 7:
            return {
                "name": parts[0],
                "temp_c": int(parts[1]),
                "gpu_util_percent": int(parts[2]),
                "mem_util_percent": int(parts[3]),
                "vram_total_mb": int(parts[4]),
                "vram_used_mb": int(parts[5]),
                "vram_free_mb": int(parts[6]),
            }
    except Exception:
        pass
    return None

def _get_cpu_info():
    cpu_percent = psutil.cpu_percent(interval=0.3)
    cpu_cores_logical = psutil.cpu_count(logical=True)
    cpu_cores_physical = psutil.cpu_count(logical=False)
    freq = psutil.cpu_freq()
    freq_current = f"{freq.current:.0f} MHz" if freq else "Unknown"
    return {
        "utilization_percent": cpu_percent,
        "cores_logical": cpu_cores_logical,
        "cores_physical": cpu_cores_physical,
        "freq": freq_current
    }

def _get_ram_info():
    mem = psutil.virtual_memory()
    return {
        "total_gb": round(mem.total / (1024**3), 1),
        "used_gb": round(mem.used / (1024**3), 1),
        "free_gb": round(mem.available / (1024**3), 1),
        "percent": mem.percent
    }

def _get_storage_info():
    drives = []
    for part in psutil.disk_partitions(all=False):
        try:
            if "cdrom" in part.opts or part.fstype == "":
                continue
            usage = psutil.disk_usage(part.mountpoint)
            drives.append({
                "mount": part.mountpoint,
                "total_gb": round(usage.total / (1024**3), 1),
                "used_gb": round(usage.used / (1024**3), 1),
                "free_gb": round(usage.free / (1024**3), 1),
                "percent": usage.percent
            })
        except Exception:
            continue
    return drives

def _get_battery_info():
    battery = psutil.sensors_battery()
    if not battery:
        return None
    return {
        "percent": battery.percent,
        "plugged": battery.power_plugged,
        "secs_left": battery.secsleft if battery.secsleft > 0 else None
    }

@tool("system_monitor", args_schema=SystemMonitorInput)
def system_monitor(category: Optional[str] = "all") -> str:
    """
    Monitor and retrieve real-time laptop system diagnostics including CPU load, RAM utilization,
    storage drive space, NVIDIA GPU utilization & temperature, and battery power status.
    """
    report = []
    cat = (category or "all").lower().strip()

    # CPU
    if cat in ("all", "cpu", "performance"):
        cpu = _get_cpu_info()
        report.append(
            f"💻 **CPU Performance**:\n"
            f"  • Utilization: {cpu['utilization_percent']}%\n"
            f"  • Cores: {cpu['cores_physical']} Physical / {cpu['cores_logical']} Logical\n"
            f"  • Frequency: {cpu['freq']}"
        )

    # RAM
    if cat in ("all", "ram", "memory", "performance"):
        ram = _get_ram_info()
        report.append(
            f"🧠 **RAM (Memory) Usage**:\n"
            f"  • Total: {ram['total_gb']} GB\n"
            f"  • Used: {ram['used_gb']} GB ({ram['percent']}%)\n"
            f"  • Free / Available: {ram['free_gb']} GB"
        )

    # GPU
    if cat in ("all", "gpu", "graphics", "temperature", "temp"):
        gpu = _get_gpu_info()
        if gpu:
            report.append(
                f"🎮 **GPU Status & Temperature**:\n"
                f"  • Model: {gpu['name']}\n"
                f"  • Temperature: {gpu['temp_c']}°C\n"
                f"  • Core Utilization: {gpu['gpu_util_percent']}%\n"
                f"  • VRAM: {gpu['vram_used_mb']} MB / {gpu['vram_total_mb']} MB ({round(gpu['vram_used_mb']/gpu['vram_total_mb']*100, 1)}%)"
            )
        else:
            report.append("🎮 **GPU**: No dedicated NVIDIA GPU or telemetry tool detected.")

    # Storage
    if cat in ("all", "storage", "disk", "drive"):
        drives = _get_storage_info()
        drive_lines = []
        for d in drives:
            drive_lines.append(f"  • Drive {d['mount']}: {d['used_gb']} GB used of {d['total_gb']} GB ({d['percent']}% used, {d['free_gb']} GB free)")
        report.append(f"💾 **Storage Drives**:\n" + "\n".join(drive_lines))

    # Battery
    if cat in ("all", "battery", "power"):
        bat = _get_battery_info()
        if bat:
            state = "Plugged in (Charging)" if bat["plugged"] else "On Battery"
            report.append(
                f"🔋 **Battery & Power**:\n"
                f"  • Level: {bat['percent']}%\n"
                f"  • Status: {state}"
            )

    return "\n\n".join(report)

def get_tool() -> StructuredTool:
    return system_monitor

