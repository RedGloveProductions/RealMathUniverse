# RealMathUniverse v0.1C File Naming Notes

## Reason for this update

The old summaries used names like:

```text
run_summary_20260503_221605_utc.json
```

That makes it difficult to tell which run used GPU, which run used CPU fallback, which profile ran, and which version produced the file.

## New run summary filename format

```text
RealMathUniverse_v0_1C_<profile>_<backend>_<GPU_or_CPU>_<YYYYMMDD_HHMMSS_UTC>_run_summary.json
```

## Example

```text
RealMathUniverse_v0_1C_preview_torch_mps_GPU_20260503_221605_UTC_run_summary.json
```

## Latest summary alias

Every run also writes:

```text
output/run_summaries/LATEST_RUN_SUMMARY.json
```

Use that when you only need the newest run and do not want to hunt through timestamps.

## Going-forward naming standard

Use this general order:

```text
Project_Version_Profile_or_Module_Backend_or_Target_Timestamp_Type.ext
```

Examples:

```text
RealMathUniverse_v0_1C_preview_torch_mps_GPU_20260503_221605_UTC_run_summary.json
RealMathUniverse_v0_2B_curvature_field_torch_mps_GPU_20260504_013000_UTC_benchmark.json
RealMathUniverse_v0_3A_desktop_opengl_renderer_20260505_210000_UTC_capture.png
RealMathUniverse_v0_4A_crab_mapper_dataset_calibration_20260506_120000_UTC_report.json
```
