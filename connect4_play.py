# Copyright 2019 DeepMind Technologies Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""DQN agents trained on Breakthrough by independent Q-learning."""

from absl import app
from absl import flags
from absl import logging
import numpy as np
import tensorflow.compat.v1 as tf

from open_spiel.python import rl_environment
from open_spiel.python.algorithms import dqn
from open_spiel.python.algorithms import random_agent

FLAGS = flags.FLAGS

# Training parameters
flags.DEFINE_string("checkpoint_dir", "/tmp/dqn_test",
                    "Directory to save/load the agent models.")
flags.DEFINE_integer(
    "save_every", int(1e4),
    "Episode frequency at which the DQN agent models are saved.")
flags.DEFINE_integer("num_train_episodes", int(1e6),
                     "Number of training episodes.")
flags.DEFINE_integer(
    "eval_every", 1000,
    "Episode frequency at which the DQN agents are evaluated.")

# DQN model hyper-parameters
flags.DEFINE_list("hidden_layers_sizes", [64, 64],
                  "Number of hidden units in the Q-Network MLP.")
flags.DEFINE_integer("replay_buffer_capacity", int(1e5),
                     "Size of the replay buffer.")
flags.DEFINE_integer("batch_size", 32,
                     "Number of transitions to sample at each learning step.")


def eval_against_opponent(env, agents, num_episodes):
  """Evaluates `trained_agents` against `random_agents` for `num_episodes`."""
  sum_episode_rewards = np.zeros(2)
  for player_pos in range(2):
    for _ in range(num_episodes):
      time_step = env.reset()
      episode_rewards = 0
      while not time_step.last():
        agent_id = time_step.observations["current_player"]
        agent_output = agents[agent_id].step(
            time_step, is_evaluation=True)
        action_list = [agent_output.action]
        time_step = env.step(action_list)
        episode_rewards += time_step.rewards[player_pos]
      sum_episode_rewards[player_pos] += episode_rewards
  return sum_episode_rewards / num_episodes


def play(env, agents):
  """Evaluates `trained_agents` against `random_agents` for `num_episodes`."""

  time_step = env.reset()
  episode_rewards = 0
  while not time_step.last():
    agent_id = time_step.observations["current_player"]
    if env.is_turn_based:
      agent_output = agents[agent_id].step(
          time_step, is_evaluation=True)
      action_list = [agent_output.action]

    time_step = env.step(action_list)
    print(str(env._state))


def main(_):
  game = "connect_four"
  num_players = 2

#   env_configs = {"columns": 5, "rows": 5}
  env = rl_environment.Environment(game)
  info_state_size = env.observation_spec()["info_state"][0]
  num_actions = env.action_spec()["num_actions"]

  with tf.Session() as sess:
    hidden_layers_sizes = [int(l) for l in FLAGS.hidden_layers_sizes]
    # pylint: disable=g-complex-comprehension

    learned = dqn.DQN(
            session=sess,
            player_id=0,
            state_representation_size=info_state_size,
            num_actions=num_actions,
            hidden_layers_sizes=hidden_layers_sizes,
            replay_buffer_capacity=FLAGS.replay_buffer_capacity,
            batch_size=FLAGS.batch_size)

    opponent = random_agent.RandomAgent(player_id=1, num_actions=num_actions)

    learned.restore("/tmp/dqn_test")

    agents = [
        learned,
        opponent,
    ]

    sess.run(tf.global_variables_initializer())

    r_mean = eval_against_opponent(env, agents, 1000)
    logging.info("Mean episode rewards %s", r_mean)

    play(env, agents)

    agents = [
        random_agent.RandomAgent(player_id=0, num_actions=num_actions),
        learned,
    ]

    learned.player_id = 1

    r_mean = eval_against_opponent(env, agents, 1000)
    logging.info("Mean episode rewards %s", r_mean)


if __name__ == "__main__":
  app.run(main)