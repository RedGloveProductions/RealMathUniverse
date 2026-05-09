# RealMathUniverse v1.6D Stepping Control Schema Repair

The 20-cycle VCV dump showed:

```text
/ch/18 voices=16 mapped=2.0, later 3.0
/ch/19 voices=16 mapped=10.0
```

That means VCV is sending behavior code and behavior gate correctly.

The failure was probably renderer-side. The v1.6C2 behavior block read behavior from the fixed Swift `vcvChannelValues[17]` and `[18]` array. The log proves `/ch/18` and `/ch/19` are present in `vcv_state.json`, but older Swift arrays can miss or lag channels above the earlier fixed channel range.

v1.6D repairs this by reading behavior directly from the JSON dictionaries:

```swift
json["channels"]["/ch/18"]
json["channels"]["/ch/19"]
json["channel_voice_counts"]["/ch/18"]
json["channel_voice_counts"]["/ch/19"]
```

It also relabels bridge display names:

```text
/ch/18 = behavior_code
/ch/19 = behavior_authority_gate
```

## Final behavior contract

```text
/ch/8  = scene / field layer only
/ch/18 = behavior_code, 0..7
/ch/19 = behavior_authority_gate
```

## VCV behavior stepping

```text
/ch/18:
  0V = code 0
  1V = code 1
  2V = code 2
  3V = code 3
  4V = code 4
  5V = code 5
  6V = code 6
  7V = code 7

/ch/19:
  0V  = manual Shift+E authority
  10V = VCV behavior authority
```
