import math

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from Obj import Vector2, Vector3, Path
from Utils import sign, clamp_sign

steer_multiplier = 3.0
height_threshold = 120
render = True
angry = False #Watch out!

class PathFollowerBot(BaseAgent):    
    def initialize_agent(self):
        #This runs once before the bot starts up
        self.controller = SimpleControllerState()
        self.dodge_time = 0

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        #Preprocess
        ball_location = Vector3(packet.game_ball.physics.location.x, packet.game_ball.physics.location.y, packet.game_ball.physics.location.z)
        ball_velocity = Vector3(packet.game_ball.physics.velocity.x, packet.game_ball.physics.velocity.y, packet.game_ball.physics.velocity.z)
        car = packet.game_cars[self.index]
        car_location = Vector3(car.physics.location.x, car.physics.location.y, car.physics.location.z)
        car_velocity = Vector3(car.physics.velocity.x, car.physics.velocity.y, car.physics.velocity.z)
        car_direction = get_car_facing_vector(car)
        kickoff = (ball_location.flatten().is_zero() and ball_velocity.is_zero())
        enemy_goal = Vector2(0, 5120 if car.team == 0 else -5120)
        car_velocity_magnitude_flat = car_velocity.flatten().magnitude()

        #Target location
        target_location, time = self.get_bounce(ball_location, packet.game_info.seconds_elapsed)
        if target_location is None:
            target_location = self.get_impact(ball_location, car_location, car_velocity_magnitude_flat, packet.game_info.seconds_elapsed, car.boost)
            time = 0
        if kickoff:
            target_location = ball_location
            path = None
        else:
            #car_predict = (car_location.flatten() + car_velocity.flatten() / 60)
            car_predict = car_location.flatten()
            path = Path(85, car_predict, target_location.flatten(), enemy_goal - target_location.flatten(), car_velocity_magnitude_flat, 0.04)
            target_location = path.get(5)

        #Steering and powersliding
        steer_correction_radians = car_direction.correction_to((target_location - car_location).flatten())
        self.controller.steer = clamp_sign(steer_correction_radians * -steer_multiplier)
        self.controller.handbrake = (abs(steer_correction_radians) > 1.2)

        #Speed control
        if path is None:
            target_distance = target_location.distance_flat(car_location)
        else:
            target_distance = path.get_distance(car_location)
        print(str(self.index) + ": " +  str(target_distance) + "uu")
        self.maintain_speed(car, target_distance, time, steer_correction_radians, car_velocity_magnitude_flat, kickoff)

        #Dodge and recovery
        dodge = (packet.game_info.seconds_elapsed - self.dodge_time)
        if self.handle_dodge(dodge):
            pass
        elif dodge > 1:
            self.controller.jump = False
            if car.has_wheel_contact and abs(steer_correction_radians) < 0.2 and car_velocity_magnitude_flat > 1300 and time == 0 and (kickoff or (angry and not path is None and len(path.path) < 3)):
                #Dodge
                self.dodge_time = packet.game_info.seconds_elapsed
            elif not car.has_wheel_contact:
                #Recovery
                self.recovery(car.physics.rotation)

            elif car_location.z > 350:
                #Jump from the wall
                self.controller.jump = True
                

        #Render
        if render and not path is None:
            path.render(self.renderer, car.team)

        return self.controller

    def recovery(self, rotation):
        self.controller.pitch = -clamp_sign(rotation.pitch * 0.5)
        self.controller.roll = -clamp_sign(rotation.roll * 0.5)

    def maintain_speed(self, car, distance, time, steer_correction_radians, current_speed, kickoff):
        if time == 0 or math.cos(steer_correction_radians) < 0:
            self.controller.throttle = abs(math.cos(steer_correction_radians))
            self.controller.boost = (car.has_wheel_contact and abs(steer_correction_radians) < 0.1 and not car.is_super_sonic and self.controller.throttle > 0.75)
        else:
            target_speed = distance / time
            throttle = (1 if target_speed > current_speed else (0 if target_speed > current_speed - 300 else -1))
            self.controller.boost = (car.has_wheel_contact and abs(steer_correction_radians) < 0.15 and throttle >= 1 and (target_speed > current_speed + 500 or target_speed > 1410))
            self.controller.throttle = throttle

    def handle_dodge(self, dodge):
        if dodge < 0.1:
            self.controller.jump = True
            return True
        elif dodge < 0.2:
            self.controller.jump = False
            return True
        elif dodge < 0.6:
            self.controller.jump = True
            self.controller.pitch = -1
            self.controller.roll = 0
            self.controller.yaw = 0            
            return True
        return False

    def get_bounce(self, ball_location, seconds_elapsed):
        ball_prediction = self.get_ball_prediction_struct()
        if ball_location.z < height_threshold or ball_prediction is None:
            return (None, 0)
        else:
            #Get the bounce
            for i in range(0, ball_prediction.num_slices):
                prediction_slice = ball_prediction.slices[i]
                location = prediction_slice.physics.location
                if location.z < height_threshold:
                    time = float(i) / 60.0 #time = (prediction_slice.game_seconds - seconds_elapsed)
                    return (Vector3(location.x, location.y, location.z), time)
            return (None, 0)

    def get_impact(self, ball_location, car_location, initial_velocity, seconds_elapsed, boost):
        ball_prediction = self.get_ball_prediction_struct()
        if ball_prediction is None:
            return ball_location
        
        max_velocity = min(2200, initial_velocity + 20 * boost)
            
        for i in range(1, ball_prediction.num_slices):
            prediction_slice = ball_prediction.slices[i]
            location = Vector3(prediction_slice.physics.location.x, prediction_slice.physics.location.y, prediction_slice.physics.location.z)                
            
            time = float(i) / 60.0 #time = (prediction_slice.game_seconds - seconds_elapsed)
            displacement = location.distance(car_location) - 92.75
            acceleration = 2 * (displacement - initial_velocity * time) / (time ** 2)
            
            if initial_velocity + acceleration * time <= max_velocity and acceleration < 1100:
                return location
        return ball_location

def get_car_facing_vector(car) -> Vector2:
    pitch = float(car.physics.rotation.pitch)
    yaw = float(car.physics.rotation.yaw)
    facing_x = math.cos(pitch) * math.cos(yaw)
    facing_y = math.cos(pitch) * math.sin(yaw)
    return Vector2(facing_x, facing_y)
