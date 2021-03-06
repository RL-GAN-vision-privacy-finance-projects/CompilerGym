# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""Tests for LlvmEnv.fork()."""
from time import time

from compiler_gym.envs import LlvmEnv
from compiler_gym.util.runfiles_path import runfiles_path
from tests.test_main import main

pytest_plugins = ["tests.envs.llvm.fixtures"]

EXAMPLE_BITCODE_FILE = runfiles_path(
    "CompilerGym/compiler_gym/third_party/cBench/cBench-v0/crc32.bc"
)
EXAMPLE_BITCODE_IR_INSTRUCTION_COUNT = 196


def test_fork_state(env: LlvmEnv):
    env.reset("cBench-v0/crc32")
    env.step(0)
    assert env.actions == [0]

    new_env = env.fork()
    try:
        assert new_env.benchmark == new_env.benchmark
        assert new_env.actions == env.actions
    finally:
        new_env.close()


def test_fork_reset(env: LlvmEnv):
    env.reset("cBench-v0/crc32")
    env.step(0)
    env.step(1)
    env.step(2)

    new_env = env.fork()
    try:
        new_env.step(3)

        assert env.actions == [0, 1, 2]
        assert new_env.actions == [0, 1, 2, 3]

        new_env.reset()
        assert env.actions == [0, 1, 2]
        assert new_env.actions == []
    finally:
        new_env.close()


def test_fork_custom_benchmark(env: LlvmEnv):
    benchmark = env.make_benchmark(EXAMPLE_BITCODE_FILE)
    env.reset(benchmark=benchmark)

    def ir(env):
        """Strip the ModuleID line from IR."""
        return "\n".join(env.ir.split("\n")[1:])

    try:
        new_env = env.fork()
        assert ir(env) == ir(new_env)

        new_env.reset()
        assert ir(env) == ir(new_env)
    finally:
        new_env.close()


FUZZ_TIME_SECONDS = 5
A_FEW_RANDOM_ACTIONS = 10


def test_fork_state_fuzz_test(env: LlvmEnv):
    """Run random episodes and check that fork() produces equivalent state."""
    end_time = time() + FUZZ_TIME_SECONDS
    while time() < end_time:
        env.reset()

        # Take a few warmup steps to get an environment in a random state.
        for _ in range(A_FEW_RANDOM_ACTIONS):
            _, _, done, _ = env.step(env.action_space.sample())
            if done:  # Broken episode, restart.
                break
        else:
            # Fork the environment and check that the states are equivalent.
            new_env = env.fork()
            try:
                assert env.state == new_env.state
                # Check that environment states remain equal if identical
                # subsequent steps are taken.
                for _ in range(A_FEW_RANDOM_ACTIONS):
                    action = env.action_space.sample()
                    _, _, done_a, _ = env.step(action)
                    _, _, done_b, _ = new_env.step(action)
                    assert done_a == done_b
                    if done_a:  # Broken episode, restart.
                        break
                    assert env.state == new_env.state
            finally:
                new_env.close()


if __name__ == "__main__":
    main()
