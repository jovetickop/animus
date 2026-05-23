param(
    [string]$BuildDir = "build"
)

cmake --build $BuildDir
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

ctest --test-dir $BuildDir --output-on-failure
exit $LASTEXITCODE
