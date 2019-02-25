from math import atan2, pi, sqrt, sin, cos

from Utils import sign, clamp_sign
import PFB

class Vector2:
    def __init__(self, x=0, y=0):
        self.x = float(x)
        self.y = float(y)

    def __add__(self, val):
        return Vector2(self.x + val.x, self.y + val.y)

    def __sub__(self, val):
        return Vector2(self.x - val.x, self.y - val.y)

    def correction_to(self, ideal):
        # The in-game axes are left handed, so use -x
        current_in_radians = atan2(self.y, -self.x)
        ideal_in_radians = atan2(ideal.y, -ideal.x)
        correction = ideal_in_radians - current_in_radians
        # Correct the angle
        if abs(correction) > pi:
            correction -= 2 * sign(correction) * pi
        return correction

    def to_list(self):
        return [self.x, self.y, 0]

    def distance(self, other):
        return (self - other).magnitude()

    def magnitude(self):
        return sqrt(self.x ** 2 + self.y ** 2)

    def is_zero(self):
        return self.x == 0 and self.y == 0

    def __mul__(self, scale):
        return Vector2(self.x * scale, self.y * scale)

    def __imul__(self, scale):
        return Vector2(self.x * scale, self.y * scale)

    def __truediv__(self, scale):
        return self * (1 / scale)

    def __div__(self, scale):
        return self * (1 / scale)

    def normalise(self):
        magnitude = self.magnitude()
        if magnitude == 0: return Vector2(0, 0)
        return self / magnitude

    def rotate(self, angle: float):
    	return Vector2(self.x * cos(angle) - self.y * sin(angle), self.y * cos(angle) + self.x * sin(angle))

    def __str__(self):
        return "(" + str(self.x) + ", " + str(self.y) + ", " + str(self.z) + ")"

    def confine(self):
        border = 190
        if abs(self.x) < 893 - border:
            return Vector2(max(-4096 + border, min(4096 - border, self.x)), max(-5120 - 400 + border, min(5120 + 400 - border, self.y)))
        else:
            return Vector2(max(-4096 + border, min(4096 - border, self.x)), max(-5120 + border, min(5120 - border, self.y)))

class Vector3:
    def __init__(self, x=0, y=0, z=0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def __add__(self, val):
        return Vector3(self.x + val.x, self.y + val.y, self.z + val.z)
    
    def __sub__(self, val):
        return Vector3(self.x - val.x, self.y - val.y, self.z - val.z)

    def to_list(self):
        return [self.x, self.y, self.z]

    def flatten(self):
        return Vector2(self.x, self.y)

    def distance(self, other):
        return (self - other).magnitude()

    def magnitude(self):
        return sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    def distance_flat(self, other):
        return (self - other).flatten().magnitude()

    def is_zero(self):
        return self.x == 0 and self.y == 0 and self.z == 0

class Path:
    def __init__(self, size: int, start: Vector2, destination: Vector2, destination_direction: Vector2, velocity: float, rate: float):
        self.size = size
        self.start = start
        self.path = []
        self.velocity = velocity
        self.destination = destination
        self.destination_direction = destination_direction.normalise()
        self.rate = rate
        self.generate_path()

    def generate_path(self):
        self.path = []

        #The path is generated backwards
        self.path.append(self.destination)

        #Start off the path
        lineup_distance = max(1, min(self.velocity, self.start.distance(self.destination) / 1.5))
        rotation = (self.destination_direction * -1) * lineup_distance
        location = (self.destination + rotation).confine()
        self.path.append(location)
        rotation = (rotation / lineup_distance * (self.velocity * self.rate)) #Scale down

        for i in range(self.size):
            difference = (self.start - location)
            angle = rotation.correction_to(difference) * PFB.steer_multiplier
            rotation = rotation.rotate(-clamp_sign(angle) / (0.4193 / self.rate))
            end = (location + rotation).confine()

            if end.distance(self.start) < 160: break
            self.path.append(end)
            location = end

    def render(self, renderer, team):
        if len(self.path) < 2: return
        renderer.begin_rendering("Path")
        for i in range(1, len(self.path)):
            point_a = self.path[i - 1]
            point_b = self.path[i]
            renderer.draw_line_3d(point_a.to_list(), point_b.to_list(), renderer.team_color(team) if i % 4 < 2 else renderer.white())
        renderer.end_rendering()

    #Get's a point on the path
    def get(self, index):
        #Asking for index 0, will give the last in the list
        point = self.path[max(0, len(self.path) - index - 1)] 
        return Vector3(point.x, point.y, 0)

    def get_distance(self, car_position) -> float:
        total = 0
        for i in range(0, len(self.path)):
            point_a = self.path[i]
            if i == len(self.path) - 1:
                point_b = car_position
            else:
                point_b = self.path[i + 1]
            total += point_a.distance(point_b)
        return total
        
