#!/usr/bin/env python3
"""
Benchmark Results Website Generator

Generates a static HTML website to visualize benchmark results.
Run with: ./generate_site.py
Output: site/ directory ready for Netlify deployment
"""

import csv
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass
class BenchmarkRun:
    """A single benchmark run result."""
    run_number: int
    success: bool
    iterations: int
    total_time_seconds: float
    function_coverage: Optional[str]
    total_statements_coverage: Optional[str]
    semantic_statements_coverage: Optional[str]
    alarm_count: int
    non_terminating_count: int
    error_type: Optional[str]
    error_file: Optional[str]
    tis_parsing_time: Optional[str]
    tis_value_analysis_time: Optional[str]
    log_dir: Optional[str]


@dataclass
class ModelBenchmark:
    """Benchmark results for a single model."""
    model: str
    timestamp: str
    runs: List[BenchmarkRun]
    csv_file: str


@dataclass
class Summary:
    """Summary data from a summary CSV."""
    model: str
    total_runs: int
    successes: int
    failures: int
    success_rate: str
    avg_time_seconds: float
    avg_iterations: float
    avg_alarm_count: float
    avg_function_coverage: str
    avg_stmt_coverage: str
    avg_semantic_coverage: str


@dataclass
class LogEntry:
    """A log directory with its contents."""
    name: str
    path: str
    files: List[str]
    summary: Optional[Dict[str, Any]]
    validations: List[Dict[str, Any]]
    errors: List[str]
    drivers: List[Dict[str, str]]  # filename -> content


@dataclass
class Driver:
    """A generated driver file."""
    filename: str
    model: str
    run_number: int
    content: str
    size: int


class SiteGenerator:
    """Generates the benchmark visualization website."""

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.benchmark_dir = self.base_dir / "benchmark_results"
        self.drivers_dir = self.base_dir / "drivers"
        self.logs_dir = self.base_dir / "logs"
        self.output_dir = self.base_dir / "site"

        self.benchmarks: List[ModelBenchmark] = []
        self.summaries: List[Summary] = []
        self.drivers: List[Driver] = []
        self.logs: List[LogEntry] = []

    def scan_all(self):
        """Scan all directories for data."""
        print("Scanning benchmark results...")
        self._scan_benchmarks()
        print(f"  Found {len(self.benchmarks)} model benchmarks")
        print(f"  Found {len(self.summaries)} summaries")

        print("Scanning drivers...")
        self._scan_drivers()
        print(f"  Found {len(self.drivers)} driver files")

        print("Scanning logs...")
        self._scan_logs()
        print(f"  Found {len(self.logs)} log directories")

    def _scan_benchmarks(self):
        """Scan benchmark_results directory for CSV files."""
        if not self.benchmark_dir.exists():
            return

        for csv_file in sorted(self.benchmark_dir.glob("*.csv")):
            if csv_file.name.startswith("benchmark_summary"):
                self._parse_summary_csv(csv_file)
            else:
                self._parse_model_csv(csv_file)

    def _parse_model_csv(self, csv_file: Path):
        """Parse a model benchmark CSV file."""
        # Extract model and timestamp from filename
        # Format: benchmark_MODEL_TIMESTAMP.csv
        match = re.match(r"benchmark_(.+)_(\d{8}_\d{6})\.csv", csv_file.name)
        if not match:
            return

        model = match.group(1)
        timestamp = match.group(2)

        runs = []
        with open(csv_file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                run = BenchmarkRun(
                    run_number=int(row.get("run_number", 0)),
                    success=row.get("success", "").lower() == "true",
                    iterations=int(row.get("iterations", 0)),
                    total_time_seconds=float(row.get("total_time_seconds", 0)),
                    function_coverage=row.get("function_coverage") or None,
                    total_statements_coverage=row.get("total_statements_coverage") or None,
                    semantic_statements_coverage=row.get("semantic_statements_coverage") or None,
                    alarm_count=int(row.get("alarm_count", 0)),
                    non_terminating_count=int(row.get("non_terminating_count", 0)),
                    error_type=row.get("error_type") or None,
                    error_file=row.get("error_file") or None,
                    tis_parsing_time=row.get("tis_parsing_time") or None,
                    tis_value_analysis_time=row.get("tis_value_analysis_time") or None,
                    log_dir=row.get("log_dir") or None,
                )
                runs.append(run)

        self.benchmarks.append(ModelBenchmark(
            model=model,
            timestamp=timestamp,
            runs=runs,
            csv_file=csv_file.name,
        ))

    def _parse_summary_csv(self, csv_file: Path):
        """Parse a summary CSV file."""
        with open(csv_file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                summary = Summary(
                    model=row.get("model", ""),
                    total_runs=int(row.get("total_runs", 0)),
                    successes=int(row.get("successes", 0)),
                    failures=int(row.get("failures", 0)),
                    success_rate=row.get("success_rate", "0%"),
                    avg_time_seconds=float(row.get("avg_time_seconds", 0)),
                    avg_iterations=float(row.get("avg_iterations", 0)),
                    avg_alarm_count=float(row.get("avg_alarm_count", 0)),
                    avg_function_coverage=row.get("avg_function_coverage", "N/A"),
                    avg_stmt_coverage=row.get("avg_stmt_coverage", "N/A"),
                    avg_semantic_coverage=row.get("avg_semantic_coverage", "N/A"),
                )
                self.summaries.append(summary)

    def _scan_drivers(self):
        """Scan drivers directory for C files."""
        if not self.drivers_dir.exists():
            return

        for c_file in sorted(self.drivers_dir.glob("*.c")):
            # Extract model and run number from filename
            # Format: benchmark_MODEL_RUN.c or other formats
            match = re.match(r"benchmark_(.+)_(\d+)\.c", c_file.name)
            if match:
                model = match.group(1)
                run_number = int(match.group(2))
            else:
                model = "unknown"
                run_number = 0

            content = c_file.read_text(errors="replace")

            self.drivers.append(Driver(
                filename=c_file.name,
                model=model,
                run_number=run_number,
                content=content,
                size=c_file.stat().st_size,
            ))

    def _scan_logs(self):
        """Scan logs directory for log entries."""
        if not self.logs_dir.exists():
            return

        for log_dir in sorted(self.logs_dir.iterdir()):
            if not log_dir.is_dir() or log_dir.name == "misc":
                continue

            files = sorted([f.name for f in log_dir.iterdir() if f.is_file()])

            # Parse summary.json if exists
            summary = None
            summary_files = list(log_dir.glob("*_summary.json"))
            if summary_files:
                try:
                    summary = json.loads(summary_files[0].read_text())
                except (json.JSONDecodeError, IOError):
                    pass

            # Parse validation JSONs
            validations = []
            for vf in sorted(log_dir.glob("*_validation_iter*.json")):
                try:
                    validations.append(json.loads(vf.read_text()))
                except (json.JSONDecodeError, IOError):
                    pass

            # Read error files
            errors = []
            for ef in sorted(log_dir.glob("*_error.txt")):
                try:
                    errors.append(ef.read_text())
                except IOError:
                    pass

            # Read driver files
            drivers = []
            for df in sorted(log_dir.glob("*_driver.c")):
                try:
                    drivers.append({
                        "filename": df.name,
                        "content": df.read_text(errors="replace"),
                    })
                except IOError:
                    pass

            self.logs.append(LogEntry(
                name=log_dir.name,
                path=str(log_dir),
                files=files,
                summary=summary,
                validations=validations,
                errors=errors,
                drivers=drivers,
            ))

    def generate(self):
        """Generate the website."""
        print(f"\nGenerating website in {self.output_dir}...")

        # Create output directory
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True)

        # Generate main HTML
        html = self._generate_html()
        (self.output_dir / "index.html").write_text(html)

        # Copy raw data files for download
        data_dir = self.output_dir / "data"
        data_dir.mkdir()

        if self.benchmark_dir.exists():
            for f in self.benchmark_dir.glob("*.csv"):
                shutil.copy(f, data_dir / f.name)

        print(f"Website generated successfully!")
        print(f"Open {self.output_dir / 'index.html'} to view locally")
        print(f"Deploy the '{self.output_dir}' directory to Netlify")

    def _generate_html(self) -> str:
        """Generate the main HTML page."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TIS Driver Benchmark Results</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <style>
        :root {{
            --bs-body-bg: #0d1117;
            --bs-body-color: #c9d1d9;
            --card-bg: #161b22;
            --border-color: #30363d;
        }}
        body {{
            background-color: var(--bs-body-bg);
            color: var(--bs-body-color);
        }}
        .navbar {{
            background-color: var(--card-bg) !important;
            border-bottom: 1px solid var(--border-color);
        }}
        .card {{
            background-color: var(--card-bg);
            border-color: var(--border-color);
        }}
        .table {{
            color: var(--bs-body-color);
        }}
        .table-dark {{
            --bs-table-bg: var(--card-bg);
            --bs-table-border-color: var(--border-color);
        }}
        .nav-tabs {{
            border-bottom-color: var(--border-color);
        }}
        .nav-tabs .nav-link {{
            color: #8b949e;
            border-color: transparent;
        }}
        .nav-tabs .nav-link:hover {{
            color: var(--bs-body-color);
            border-color: var(--border-color);
        }}
        .nav-tabs .nav-link.active {{
            color: var(--bs-body-color);
            background-color: var(--card-bg);
            border-color: var(--border-color) var(--border-color) var(--card-bg);
        }}
        .list-group-item {{
            background-color: var(--card-bg);
            border-color: var(--border-color);
            color: var(--bs-body-color);
        }}
        .list-group-item:hover {{
            background-color: #21262d;
        }}
        .list-group-item.active {{
            background-color: #238636;
            border-color: #238636;
        }}
        .badge-success {{ background-color: #238636; }}
        .badge-danger {{ background-color: #da3633; }}
        .badge-warning {{ background-color: #9e6a03; }}
        .code-viewer {{
            max-height: 600px;
            overflow-y: auto;
        }}
        pre code {{
            font-size: 0.85rem;
        }}
        .stat-card {{
            text-align: center;
            padding: 1.5rem;
        }}
        .stat-card .value {{
            font-size: 2.5rem;
            font-weight: bold;
            color: #58a6ff;
        }}
        .stat-card .label {{
            color: #8b949e;
            font-size: 0.9rem;
        }}
        .success-rate {{
            font-size: 1.5rem;
        }}
        .log-tree {{
            font-family: monospace;
            font-size: 0.85rem;
        }}
        .log-file {{
            cursor: pointer;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
        }}
        .log-file:hover {{
            background-color: #21262d;
        }}
        .sidebar {{
            max-height: calc(100vh - 200px);
            overflow-y: auto;
        }}
        .accordion-button {{
            background-color: var(--card-bg);
            color: var(--bs-body-color);
        }}
        .accordion-button:not(.collapsed) {{
            background-color: #21262d;
            color: var(--bs-body-color);
        }}
        .accordion-body {{
            background-color: var(--card-bg);
        }}
        .form-select, .form-control {{
            background-color: #21262d;
            border-color: var(--border-color);
            color: var(--bs-body-color);
        }}
        .form-select:focus, .form-control:focus {{
            background-color: #21262d;
            border-color: #58a6ff;
            color: var(--bs-body-color);
        }}
    </style>
</head>
<body>
    <nav class="navbar navbar-dark sticky-top">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1">
                <i class="bi bi-speedometer2"></i> TIS Driver Benchmark Results
            </span>
            <span class="text-muted small">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span>
        </div>
    </nav>

    <div class="container-fluid py-4">
        <ul class="nav nav-tabs mb-4" id="mainTabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="overview-tab" data-bs-toggle="tab" data-bs-target="#overview" type="button">
                    <i class="bi bi-graph-up"></i> Overview
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="benchmarks-tab" data-bs-toggle="tab" data-bs-target="#benchmarks" type="button">
                    <i class="bi bi-table"></i> Benchmarks
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="drivers-tab" data-bs-toggle="tab" data-bs-target="#drivers" type="button">
                    <i class="bi bi-file-code"></i> Drivers
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="logs-tab" data-bs-toggle="tab" data-bs-target="#logs" type="button">
                    <i class="bi bi-journal-text"></i> Logs
                </button>
            </li>
        </ul>

        <div class="tab-content" id="mainTabContent">
            {self._generate_overview_tab()}
            {self._generate_benchmarks_tab()}
            {self._generate_drivers_tab()}
            {self._generate_logs_tab()}
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/c.min.js"></script>
    <script>
        // Initialize syntax highlighting
        document.querySelectorAll('pre code').forEach((el) => {{
            hljs.highlightElement(el);
        }});

        // Driver viewer
        function showDriver(index) {{
            document.querySelectorAll('.driver-content').forEach(el => el.classList.add('d-none'));
            document.getElementById('driver-' + index).classList.remove('d-none');
            document.querySelectorAll('.driver-list-item').forEach(el => el.classList.remove('active'));
            document.querySelector('[data-driver="' + index + '"]').classList.add('active');
        }}

        // Log viewer
        function showLog(index) {{
            document.querySelectorAll('.log-content').forEach(el => el.classList.add('d-none'));
            document.getElementById('log-' + index).classList.remove('d-none');
            document.querySelectorAll('.log-list-item').forEach(el => el.classList.remove('active'));
            document.querySelector('[data-log="' + index + '"]').classList.add('active');
        }}

        // Filter drivers by model
        function filterDrivers() {{
            const model = document.getElementById('driverModelFilter').value;
            document.querySelectorAll('.driver-list-item').forEach(el => {{
                if (model === 'all' || el.dataset.model === model) {{
                    el.classList.remove('d-none');
                }} else {{
                    el.classList.add('d-none');
                }}
            }});
        }}

        // Search logs
        function searchLogs() {{
            const query = document.getElementById('logSearch').value.toLowerCase();
            document.querySelectorAll('.log-list-item').forEach(el => {{
                if (el.textContent.toLowerCase().includes(query)) {{
                    el.classList.remove('d-none');
                }} else {{
                    el.classList.add('d-none');
                }}
            }});
        }}
    </script>
</body>
</html>"""

    def _generate_overview_tab(self) -> str:
        """Generate the overview tab content."""
        # Calculate stats
        total_runs = sum(s.total_runs for s in self.summaries)
        total_successes = sum(s.successes for s in self.summaries)
        total_failures = sum(s.failures for s in self.summaries)
        overall_rate = f"{(total_successes / total_runs * 100):.1f}%" if total_runs > 0 else "N/A"

        # Prepare chart data
        models = [s.model for s in self.summaries]
        success_rates = [float(s.success_rate.rstrip('%')) for s in self.summaries]
        avg_times = [s.avg_time_seconds for s in self.summaries]
        avg_iterations = [s.avg_iterations for s in self.summaries]

        return f"""
            <div class="tab-pane fade show active" id="overview" role="tabpanel">
                <!-- Stats Cards -->
                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="card stat-card">
                            <div class="value">{len(self.summaries)}</div>
                            <div class="label">Models Tested</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card stat-card">
                            <div class="value">{total_runs}</div>
                            <div class="label">Total Runs</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card stat-card">
                            <div class="value text-success">{total_successes}</div>
                            <div class="label">Successes</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card stat-card">
                            <div class="value text-danger">{total_failures}</div>
                            <div class="label">Failures</div>
                        </div>
                    </div>
                </div>

                <!-- Charts -->
                <div class="row mb-4">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">Success Rate by Model</div>
                            <div class="card-body">
                                <canvas id="successRateChart"></canvas>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">Average Iterations by Model</div>
                            <div class="card-body">
                                <canvas id="iterationsChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Summary Table -->
                <div class="card">
                    <div class="card-header">
                        <i class="bi bi-table"></i> Summary
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-dark table-striped table-hover">
                                <thead>
                                    <tr>
                                        <th>Model</th>
                                        <th>Runs</th>
                                        <th>Success</th>
                                        <th>Failures</th>
                                        <th>Success Rate</th>
                                        <th>Avg Time (s)</th>
                                        <th>Avg Iterations</th>
                                        <th>Avg Alarms</th>
                                        <th>Func Coverage</th>
                                        <th>Stmt Coverage</th>
                                        <th>Semantic Coverage</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {self._generate_summary_rows()}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <script>
                    document.addEventListener('DOMContentLoaded', function() {{
                        // Success Rate Chart
                        new Chart(document.getElementById('successRateChart'), {{
                            type: 'bar',
                            data: {{
                                labels: {json.dumps(models)},
                                datasets: [{{
                                    label: 'Success Rate (%)',
                                    data: {json.dumps(success_rates)},
                                    backgroundColor: 'rgba(35, 134, 54, 0.8)',
                                    borderColor: 'rgba(35, 134, 54, 1)',
                                    borderWidth: 1
                                }}]
                            }},
                            options: {{
                                responsive: true,
                                scales: {{
                                    y: {{
                                        beginAtZero: true,
                                        max: 100,
                                        ticks: {{ color: '#8b949e' }},
                                        grid: {{ color: '#30363d' }}
                                    }},
                                    x: {{
                                        ticks: {{ color: '#8b949e' }},
                                        grid: {{ color: '#30363d' }}
                                    }}
                                }},
                                plugins: {{
                                    legend: {{ labels: {{ color: '#c9d1d9' }} }}
                                }}
                            }}
                        }});

                        // Iterations Chart
                        new Chart(document.getElementById('iterationsChart'), {{
                            type: 'bar',
                            data: {{
                                labels: {json.dumps(models)},
                                datasets: [{{
                                    label: 'Avg Iterations',
                                    data: {json.dumps(avg_iterations)},
                                    backgroundColor: 'rgba(88, 166, 255, 0.8)',
                                    borderColor: 'rgba(88, 166, 255, 1)',
                                    borderWidth: 1
                                }}]
                            }},
                            options: {{
                                responsive: true,
                                scales: {{
                                    y: {{
                                        beginAtZero: true,
                                        ticks: {{ color: '#8b949e' }},
                                        grid: {{ color: '#30363d' }}
                                    }},
                                    x: {{
                                        ticks: {{ color: '#8b949e' }},
                                        grid: {{ color: '#30363d' }}
                                    }}
                                }},
                                plugins: {{
                                    legend: {{ labels: {{ color: '#c9d1d9' }} }}
                                }}
                            }}
                        }});
                    }});
                </script>
            </div>"""

    def _generate_summary_rows(self) -> str:
        """Generate table rows for summary data."""
        rows = []
        for s in self.summaries:
            rate_class = "text-success" if float(s.success_rate.rstrip('%')) >= 50 else "text-danger"
            rows.append(f"""
                <tr>
                    <td><strong>{escape(s.model)}</strong></td>
                    <td>{s.total_runs}</td>
                    <td class="text-success">{s.successes}</td>
                    <td class="text-danger">{s.failures}</td>
                    <td class="{rate_class}"><strong>{s.success_rate}</strong></td>
                    <td>{s.avg_time_seconds:.2f}</td>
                    <td>{s.avg_iterations:.2f}</td>
                    <td>{s.avg_alarm_count:.2f}</td>
                    <td>{s.avg_function_coverage}</td>
                    <td>{s.avg_stmt_coverage}</td>
                    <td>{s.avg_semantic_coverage}</td>
                </tr>""")
        return "".join(rows)

    def _generate_benchmarks_tab(self) -> str:
        """Generate the benchmarks tab content."""
        # Group benchmarks by model
        models = sorted(set(b.model for b in self.benchmarks))

        accordion_items = []
        for i, model in enumerate(models):
            model_benchmarks = [b for b in self.benchmarks if b.model == model]

            tables = []
            for bench in model_benchmarks:
                tables.append(f"""
                    <h6 class="mt-3"><i class="bi bi-file-earmark-text"></i> {bench.csv_file}</h6>
                    <div class="table-responsive">
                        <table class="table table-dark table-sm table-striped">
                            <thead>
                                <tr>
                                    <th>Run</th>
                                    <th>Status</th>
                                    <th>Iterations</th>
                                    <th>Time (s)</th>
                                    <th>Coverage</th>
                                    <th>Alarms</th>
                                    <th>Error Type</th>
                                </tr>
                            </thead>
                            <tbody>
                                {self._generate_benchmark_rows(bench.runs)}
                            </tbody>
                        </table>
                    </div>""")

            accordion_items.append(f"""
                <div class="accordion-item">
                    <h2 class="accordion-header">
                        <button class="accordion-button {'collapsed' if i > 0 else ''}" type="button"
                                data-bs-toggle="collapse" data-bs-target="#bench-{i}">
                            <i class="bi bi-cpu"></i>&nbsp; {escape(model)}
                            <span class="badge bg-secondary ms-2">{len(model_benchmarks)} file(s)</span>
                        </button>
                    </h2>
                    <div id="bench-{i}" class="accordion-collapse collapse {'show' if i == 0 else ''}">
                        <div class="accordion-body">
                            {"".join(tables)}
                        </div>
                    </div>
                </div>""")

        download_links = []
        if self.benchmark_dir.exists():
            for f in sorted(self.benchmark_dir.glob("*.csv")):
                download_links.append(f'<a href="data/{f.name}" class="btn btn-sm btn-outline-secondary me-2 mb-2"><i class="bi bi-download"></i> {f.name}</a>')

        return f"""
            <div class="tab-pane fade" id="benchmarks" role="tabpanel">
                <div class="card mb-4">
                    <div class="card-header">
                        <i class="bi bi-download"></i> Download CSV Files
                    </div>
                    <div class="card-body">
                        {"".join(download_links) if download_links else "<em>No CSV files available</em>"}
                    </div>
                </div>

                <div class="accordion" id="benchmarksAccordion">
                    {"".join(accordion_items) if accordion_items else "<p>No benchmark data found</p>"}
                </div>
            </div>"""

    def _generate_benchmark_rows(self, runs: List[BenchmarkRun]) -> str:
        """Generate table rows for benchmark runs."""
        rows = []
        for r in runs:
            status_badge = '<span class="badge bg-success">Success</span>' if r.success else '<span class="badge bg-danger">Failed</span>'
            coverage = f"{r.function_coverage}" if r.function_coverage else "-"
            error_type = escape(r.error_type) if r.error_type else "-"

            rows.append(f"""
                <tr>
                    <td>{r.run_number}</td>
                    <td>{status_badge}</td>
                    <td>{r.iterations}</td>
                    <td>{r.total_time_seconds:.2f}</td>
                    <td>{coverage}</td>
                    <td>{r.alarm_count}</td>
                    <td><small>{error_type}</small></td>
                </tr>""")
        return "".join(rows)

    def _generate_drivers_tab(self) -> str:
        """Generate the drivers tab content."""
        models = sorted(set(d.model for d in self.drivers))

        model_options = ['<option value="all">All Models</option>']
        for m in models:
            model_options.append(f'<option value="{escape(m)}">{escape(m)}</option>')

        driver_list = []
        driver_contents = []

        for i, driver in enumerate(self.drivers):
            active = "active" if i == 0 else ""
            driver_list.append(f"""
                <a href="javascript:void(0)" onclick="showDriver({i})"
                   class="list-group-item list-group-item-action driver-list-item {active}"
                   data-driver="{i}" data-model="{escape(driver.model)}">
                    <div class="d-flex justify-content-between align-items-center">
                        <span><i class="bi bi-file-code"></i> {escape(driver.filename)}</span>
                        <small class="text-info">{driver.size} bytes</small>
                    </div>
                    <small class="text-secondary">Model: {escape(driver.model)} | Run: {driver.run_number}</small>
                </a>""")

            hidden = "" if i == 0 else "d-none"
            driver_contents.append(f"""
                <div id="driver-{i}" class="driver-content {hidden}">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <h5><i class="bi bi-file-code"></i> {escape(driver.filename)}</h5>
                        <span class="badge bg-secondary">{driver.size} bytes</span>
                    </div>
                    <div class="code-viewer">
                        <pre><code class="language-c">{escape(driver.content)}</code></pre>
                    </div>
                </div>""")

        return f"""
            <div class="tab-pane fade" id="drivers" role="tabpanel">
                <div class="row">
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-header">
                                <select id="driverModelFilter" class="form-select form-select-sm" onchange="filterDrivers()">
                                    {"".join(model_options)}
                                </select>
                            </div>
                            <div class="list-group list-group-flush sidebar">
                                {"".join(driver_list) if driver_list else "<p class='p-3'>No drivers found</p>"}
                            </div>
                        </div>
                    </div>
                    <div class="col-md-9">
                        <div class="card">
                            <div class="card-body">
                                {"".join(driver_contents) if driver_contents else "<p>Select a driver to view its contents</p>"}
                            </div>
                        </div>
                    </div>
                </div>
            </div>"""

    def _generate_logs_tab(self) -> str:
        """Generate the logs tab content."""
        log_list = []
        log_contents = []

        for i, log in enumerate(self.logs):
            active = "active" if i == 0 else ""

            # Determine status from summary or validations
            status_badge = '<span class="badge bg-secondary">Unknown</span>'
            if log.summary:
                if log.summary.get("success"):
                    status_badge = '<span class="badge bg-success">Success</span>'
                else:
                    status_badge = '<span class="badge bg-danger">Failed</span>'
            elif log.validations:
                last_valid = log.validations[-1]
                if last_valid.get("is_valid"):
                    status_badge = '<span class="badge bg-success">Success</span>'
                else:
                    status_badge = '<span class="badge bg-danger">Failed</span>'

            log_list.append(f"""
                <a href="javascript:void(0)" onclick="showLog({i})"
                   class="list-group-item list-group-item-action log-list-item {active}" data-log="{i}">
                    <div class="d-flex justify-content-between align-items-center">
                        <span><i class="bi bi-folder"></i> {escape(log.name)}</span>
                        {status_badge}
                    </div>
                    <small class="text-info">{len(log.files)} files</small>
                </a>""")

            hidden = "" if i == 0 else "d-none"
            log_contents.append(self._generate_log_content(i, log, hidden))

        return f"""
            <div class="tab-pane fade" id="logs" role="tabpanel">
                <div class="row">
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-header">
                                <input type="text" id="logSearch" class="form-control form-control-sm"
                                       placeholder="Search logs..." onkeyup="searchLogs()">
                            </div>
                            <div class="list-group list-group-flush sidebar">
                                {"".join(log_list) if log_list else "<p class='p-3'>No logs found</p>"}
                            </div>
                        </div>
                    </div>
                    <div class="col-md-9">
                        {"".join(log_contents) if log_contents else "<p>Select a log to view details</p>"}
                    </div>
                </div>
            </div>"""

    def _generate_log_content(self, index: int, log: LogEntry, hidden: str) -> str:
        """Generate content for a single log entry."""
        # Files list
        files_html = "<ul class='log-tree'>"
        for f in log.files:
            icon = "bi-file-code" if f.endswith(".c") else "bi-file-text" if f.endswith(".json") else "bi-file"
            files_html += f"<li><i class='bi {icon}'></i> {escape(f)}</li>"
        files_html += "</ul>"

        # Summary
        summary_html = ""
        if log.summary:
            summary_html = f"""
                <div class="card mb-3">
                    <div class="card-header"><i class="bi bi-info-circle"></i> Summary</div>
                    <div class="card-body">
                        <pre><code class="language-json">{escape(json.dumps(log.summary, indent=2))}</code></pre>
                    </div>
                </div>"""

        # Validations
        validations_html = ""
        if log.validations:
            val_items = []
            for v in log.validations:
                status = "success" if v.get("is_valid") else "danger"
                iter_num = v.get("iteration", "?")
                val_items.append(f"""
                    <div class="accordion-item">
                        <h2 class="accordion-header">
                            <button class="accordion-button collapsed" type="button"
                                    data-bs-toggle="collapse" data-bs-target="#val-{index}-{iter_num}">
                                <span class="badge bg-{status} me-2">Iter {iter_num}</span>
                                {"Valid" if v.get("is_valid") else "Invalid"}
                            </button>
                        </h2>
                        <div id="val-{index}-{iter_num}" class="accordion-collapse collapse">
                            <div class="accordion-body">
                                <pre><code class="language-json">{escape(json.dumps(v, indent=2))}</code></pre>
                            </div>
                        </div>
                    </div>""")

            validations_html = f"""
                <div class="card mb-3">
                    <div class="card-header"><i class="bi bi-check-circle"></i> Validations</div>
                    <div class="card-body">
                        <div class="accordion" id="validations-{index}">
                            {"".join(val_items)}
                        </div>
                    </div>
                </div>"""

        # Errors
        errors_html = ""
        if log.errors:
            error_items = []
            for j, err in enumerate(log.errors):
                error_items.append(f"""
                    <div class="mb-3">
                        <strong>Error {j + 1}:</strong>
                        <pre class="bg-dark p-2 mt-2" style="max-height: 200px; overflow-y: auto;"><code>{escape(err)}</code></pre>
                    </div>""")

            errors_html = f"""
                <div class="card mb-3 border-danger">
                    <div class="card-header text-danger"><i class="bi bi-exclamation-triangle"></i> Errors</div>
                    <div class="card-body">
                        {"".join(error_items)}
                    </div>
                </div>"""

        # Drivers
        drivers_html = ""
        if log.drivers:
            driver_items = []
            for j, drv in enumerate(log.drivers):
                driver_items.append(f"""
                    <div class="accordion-item">
                        <h2 class="accordion-header">
                            <button class="accordion-button collapsed" type="button"
                                    data-bs-toggle="collapse" data-bs-target="#drv-{index}-{j}">
                                <i class="bi bi-file-code me-2"></i> {escape(drv['filename'])}
                            </button>
                        </h2>
                        <div id="drv-{index}-{j}" class="accordion-collapse collapse">
                            <div class="accordion-body code-viewer">
                                <pre><code class="language-c">{escape(drv['content'])}</code></pre>
                            </div>
                        </div>
                    </div>""")

            drivers_html = f"""
                <div class="card mb-3">
                    <div class="card-header"><i class="bi bi-file-code"></i> Generated Drivers</div>
                    <div class="card-body">
                        <div class="accordion" id="drivers-{index}">
                            {"".join(driver_items)}
                        </div>
                    </div>
                </div>"""

        return f"""
            <div id="log-{index}" class="log-content {hidden}">
                <div class="card mb-3">
                    <div class="card-header">
                        <h5><i class="bi bi-folder"></i> {escape(log.name)}</h5>
                    </div>
                    <div class="card-body">
                        <strong>Files:</strong>
                        {files_html}
                    </div>
                </div>
                {summary_html}
                {validations_html}
                {errors_html}
                {drivers_html}
            </div>"""


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate benchmark visualization website")
    parser.add_argument("--base-dir", "-d", default=".", help="Base directory containing benchmark data")
    parser.add_argument("--output", "-o", default="site", help="Output directory for the website")

    args = parser.parse_args()

    generator = SiteGenerator(args.base_dir)
    generator.output_dir = Path(args.base_dir) / args.output

    generator.scan_all()
    generator.generate()


if __name__ == "__main__":
    main()
