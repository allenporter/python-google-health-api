---
name: python_best_practices
description: Broad Python architectural and coding best practices focusing on typing, error handling, caching, and object-oriented delegation.
---

# Python Development Best Practices

When writing or refactoring Python code in this repository, follow these general guidelines to ensure the codebase remains maintainable, performant, and type-safe.

## 1. Type Hinting and Annotations
* **Modern Typing (Python 3.10+):** Use modern typing features natively available in newer Python versions (such as unquoted forward references where applicable). Do NOT use `from __future__ import annotations`, as the repository targets a newer version of Python.
* **Return Self:** Use `typing.Self` instead of string literals when a method returns an instance of its own class.

## 2. Exception Handling and Boundaries
* **Narrow Exception Scopes:** Never use bare `except Exception:` unless explicitly logging and re-raising. Catch only narrow, specific exceptions (e.g., `ValueError`, `KeyError`) to prevent accidentally swallowing unrelated programming errors.
* **Encapsulate Internal Errors:** When writing parsers, SDK wrappers, or low-level utilities, do not leak internal system exceptions (like `IndexError` or `KeyError`) to the caller. Wrap them and raise a single, domain-specific exception (e.g., `ParseError`, `ApiError`).

## 3. Performance and Caching
* **Property Caching:** Use `@cached_property` from the standard `functools` module for lazy evaluation of expensive properties or to cache state (e.g., converting a list to a dictionary for O(1) lookups), but **only when relevant for long-lived objects** (such as keysets that are kept in memory across multiple requests).
* **Deterministic Caching:** Use `@cache` (or `@lru_cache`) for pure functions with deterministic outputs (like reflection or metadata extraction) to eliminate repeated execution overhead.

## 4. Object-Oriented Delegation
* **Avoid Monolithic Functions:** Break down large functions that handle parsing, transformation, and business logic into smaller, delegated responsibilities.
* **Direct Domain Object Construction:** Deserialization methods should parse raw inputs and directly return the final usable domain object (e.g., a standard cryptographic key) rather than an intermediate Data Transfer Object (DTO) that the caller must manually convert.
* **Encapsulate Validation:** Delegate validation and verification logic to the specific domain objects that own the data, rather than having container classes manage the internals of their children.

## 5. Modern Python Syntax
* **Walrus Operator:** Utilize the walrus operator (`:=`) to flatten conditional logic, such as checking dictionary membership and assigning the result in a single step (`if (match := mapping.get(key)) is None:`).
