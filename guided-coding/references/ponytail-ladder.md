# Ponytail Decision Ladder

Apply this ladder to every piece of guidance, test, and template you produce.

1. **Does this need to exist?**  
   If the feature or line is not required for the current test to pass → delete it (YAGNI).

2. **Already in this codebase?**  
   Search the existing code. Reuse the function, type, or pattern that is already there.

3. **Does the language standard library solve it?**  
   Prefer built-ins (`map`, `filter`, `Intl`, `datetime`, etc.) over custom code.

4. **Is there a native platform feature?**  
   Browser has `<input type="date">`. OS has the right tool. Use it.

5. **Is there an already-installed dependency that does it?**  
   Use the one that is already in `package.json` / `requirements.txt` / etc. Do not add new ones unless the human explicitly asks.

6. **Can it be expressed in one line or one expression?**  
   Prefer that. One clear line is better than a five-line helper.

7. **Only then: write the absolute minimum that works.**  
   Still keep validation, security boundaries, and error paths that matter.

## Additional rules

- Lazy ≠ negligent. Never remove trust-boundary checks, data-loss protection, security, or accessibility for the sake of fewer lines.
- Code is small because it is necessary, not because it is golfed.
- When the human shows over-engineered code, quote the ladder step that was violated and give the simpler alternative immediately.
