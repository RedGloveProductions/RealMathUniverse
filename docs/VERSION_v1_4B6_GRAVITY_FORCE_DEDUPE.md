# RealMathUniverse v1.4B6 Gravity Force Dedupe

The v1.4B5 cleanup correctly removed the stale encoder overwrite, but the Metal shader still had two gravity-well force blocks in the same compute scope. That caused the Metal pipeline failure:

```text
redefinition of 'wellPos'
redefinition of 'wellStrength'
redefinition of 'gravityWellCenter'
redefinition of 'toWell'
redefinition of 'wellDistance'
redefinition of 'wellDir'
redefinition of 'wellTangent'
```

v1.4B6 keeps one gravity-well block and removes later duplicate `wellPos` blocks.

The surviving path is:

```text
/ch/13 -> vcv_state/control_state -> vcvRawChannelValues[12] -> gravityWellPosition buffer 18
/ch/14 -> vcv_state/control_state -> vcvRawChannelValues[13] -> gravityWellStrength buffer 19
Metal shader -> one controllable gravity-well force block
```
