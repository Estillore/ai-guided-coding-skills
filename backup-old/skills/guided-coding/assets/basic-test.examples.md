# Minimal Test Examples

Use the simplest assertion that proves the behavior.

## JavaScript / TypeScript (Jest / Vitest style)

```ts
test("returns the expected value for valid input", () => {
  expect(functionName(validInput)).toBe(expected);
});

test("handles the main failure case", () => {
  expect(() => functionName(invalidInput)).toThrow();
  // or
  expect(functionName(invalidInput)).toBeNull();
});
```

## PHP (PHPUnit style)

```php
public function test_returns_expected_value_for_valid_input(): void
{
    $this->assertSame($expected, functionName($validInput));
}

public function test_handles_main_failure_case(): void
{
    $this->expectException(SomeException::class);
    functionName($invalidInput);
}
```

Start with one happy-path test + one important failure test. Add more only when needed.
