import argparse
import numpy as np
import matplotlib.pyplot as plt
import time

import robosuite
import robosuite.utils.transform_utils as T
from robosuite.wrappers import IKWrapper

import waypoint_policies
import recorder

if __name__ == "__main__":

    ### <SETTINGS>
    # preview_mode = False
    preview_mode = False
    vis_images = False
    record_name = "data/pullset-400.hdf5"
    # output_file =
    ### </SETTINGS>

    if preview_mode:
        vis_images = False

    env = robosuite.make(
        "PandaDoor",
        has_renderer=preview_mode,
        ignore_done=True,
        use_camera_obs=(not preview_mode),
        camera_name="birdview",
        camera_height=32,
        camera_width=32,
        gripper_visualization=True,
        reward_shaping=True,
        control_freq=20,
        controller='position',
    )

    recorder = recorder.ObservationRecorder(record_name)

    for rollout_index in range(400):
        obs = env.reset()
        # env.viewer.set_camera(camera_id=0)
        if preview_mode:
            env.render()
        env.controller.step = 0.
        env.controller.last_goal_position = np.array((0, 0, 0))
        env.controller.last_goal_orientation = np.eye(3)

        # Initialize training policy
        # policy = waypoint_policies.PushWaypointPolicy()
        policy = waypoint_policies.PullWaypointPolicy()

        # Set initial joint and door position
        initial_joints, initial_door = policy.get_initial_state()
        env.set_robot_joint_positions(initial_joints)
        env.sim.data.qpos[env.sim.model.get_joint_qpos_addr(
            "door_hinge")] = initial_door

        q_limit_counter = 0

        if vis_images:
            plt.figure()
            plt.ion()
            plt.show()

        max_iteration_count = 800
        for i in range(max_iteration_count):
            print("#{}:{}".format(rollout_index, i))
            action = policy.update(env)
            obs, reward, done, info = env.step(action)
            if preview_mode:
                env.render()

            if env._check_q_limits():
                q_limit_counter += 1
                termination_cause = "joint limits"
            elif not obs['contact-obs']:
                q_limit_counter += 1
                termination_cause = "missing contact"
            else:
                q_limit_counter *= 0.9

            if q_limit_counter > 400:
                break

            if vis_images:
                start = time.time()
                plt.imshow(obs['image'], cmap='gray')
                plt.draw()
                plt.pause(0.0001)

            if type(policy) == waypoint_policies.PushWaypointPolicy:
                if env.sim.data.qpos[env.sim.model.get_joint_qpos_addr(
                        "door_hinge")] < 0.01:
                    termination_cause = "closed door"
                    break

            recorder.push(obs)
            ### obs keys:
            # 'joint_pos'
            # 'joint_vel'
            # 'gripper_qpos'
            # 'gripper_qvel'
            # 'eef_pos'
            # 'eef_quat'
            # 'eef_vlin'
            # 'eef_vang'
            # 'robot-state'
            # 'prev-act'
            # 'contact-obs'
            # 'ee-force-obs'
            # 'ee-torque-obs'
            # 'object-state'
            # 'image'

        recorder.save()

        if i == max_iteration_count - 1:
            termination_cause = "max iteration"
        print(
            "Terminated rollout #{}: {}".format(
                rollout_index,
                termination_cause))
