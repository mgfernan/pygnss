# CHANGELOG


## v0.7.0 (2025-03-24)

### Features

- **ionex_diff**: Add option to compute diffs relative to NeQuick
  ([`9eec31f`](https://github.com/mgfernan/pygnss/commit/9eec31f85ccc8fcf76e8ad5326876c8d4833a962))


## v0.6.0 (2025-03-23)

### Features

- **ionex**: Expose ionex diff as client program
  ([`a9175ea`](https://github.com/mgfernan/pygnss/commit/a9175eab5e7183b0ddd604dc48c0fd4bd3b0a856))


## v0.5.0 (2025-03-22)

### Features

- **ionex**: Add subtract IONEX files
  ([`2bcd2a8`](https://github.com/mgfernan/pygnss/commit/2bcd2a892296ac3290761d4f1f017390f21ba130))

Feature to compute the difference between two IONEX files. Tests have been added to check this
  feature


## v0.4.0 (2025-03-21)

### Features

- **iono**: Add Gim class and subtraction operation
  ([`d7bc63a`](https://github.com/mgfernan/pygnss/commit/d7bc63a4cfd251cec007af5dc70c45d387cd3470))


## v0.3.0 (2025-03-21)

### Features

- **nequick**: Add to_ionex method
  ([`c24da02`](https://github.com/mgfernan/pygnss/commit/c24da02318883aeb1f3509e9957e969a85e5ac34))


## v0.2.0 (2025-02-19)

### Features

- **filter**: Add kwargs in ekf/ukf process
  ([`8007178`](https://github.com/mgfernan/pygnss/commit/800717873861525d7f59cfcf08198141bc8d1fd8))

The kwargs allows add metadata to the handler of the solution


## v0.1.1 (2025-02-05)

### Bug Fixes

- **_c_ext**: Add cycle slip column
  ([`2ac6611`](https://github.com/mgfernan/pygnss/commit/2ac66114c622cdfec18f9e636b87a9662e2d38f0))

Computed from the LLI phase flag


## v0.1.0 (2025-02-05)

### Features

- First import with basic libraries
  ([`7844517`](https://github.com/mgfernan/pygnss/commit/7844517863b8c4da7bc1f6edba54f118d46b507d))

- **filter**: Add UKF and EKF filters
  ([`5e98739`](https://github.com/mgfernan/pygnss/commit/5e98739d944a54137db8e6c9ef501b1ffcb24e86))

### Refactoring

- **submodules**: Move hatanakalib to submodules folder
  ([`786882b`](https://github.com/mgfernan/pygnss/commit/786882b65fcd72b9e3b746d482bfa5148e12b641))
