import hashlib
import logging
import json
import requests
import time


class HueException(BaseException):
    def __init__(self, msg):
        self.msg = msg


class PyHugh(object):
    def __init__(self, bridge_ip, username=None):
        self.logger = logging.getLogger('pyhue')
        self.bridge_ip = bridge_ip
        self.devicetype = "PyHugh"
        self.username = username

    def authenticate(self, retry_delay=10, attempts=6):
        for i in range(0, attempts):
            r = requests.post(
                'http://{}/api'.format(self.bridge_ip),
                data=json.dumps({
                    'devicetype': self.devicetype,
                }))
            resp = json.loads(r.text)

            if type(resp) == list and len(resp) > 0:
                if 'success' in resp[0]:
                    self.username = resp[0]['success']['username']
                    print(self.username)
                    return True
                elif 'error' in resp[0]:
                    if resp[0]['error'].get('type', None) == 101:
                        self.logger.warning("Go press your button!")
                    else:
                        raise HueException(resp[0]['error'])

            time.sleep(retry_delay)

        return False

    def request(self, path, method='GET', **kwargs):
        self.logger.debug(path)
        uri = 'http://{ip}/api/{username}{path}'.format(
            ip=self.bridge_ip,
            username=self.username,
            path=path)
        r = requests.request(method, uri, **kwargs)
        resp = json.loads(r.text)

        if isinstance(resp, list) and resp[0].get('error', None):
            if resp[0]['error'].get('type', None) == 1:
                if self.authenticate():
                    return self.request(path, method, **kwargs)
            raise HueException(resp[0]['error'])

        return resp

    @property
    def state(self):
        resp = self.request('')
        return resp

    @property
    def lights(self):
        return self.request_to_property('/lights', ColorLight)

    def light_action(self, light_id, newstate):
        return self.request('/lights/{0}/state'.format(light_id),
                            method='PUT',
                            data=json.dumps(newstate))

    @property
    def groups(self):
        groups = self.request_to_property('/groups', Group)

        # group id 0 = all lights
        groups['0'] = Group(0, {
            'name': "All Lights",
            'lights': self.lights,
        })

        return groups

    def create_group(self, name, lights=[]):
        if len(lights) < 1:
            return

        data = {
            'name': name,
            'lights': [str(x) for x in lights],
        }
        return self.request('/groups', method='POST', data=json.dumps(data))

    def group_action(self, group_id, newstate):
        return self.request('/groups/{0}/action'.format(group_id),
                            method='PUT',
                            data=json.dumps(newstate))

    def delete_group(self, group):
        return self.request('/groups/{0}'.format(group.group_id),
                            method='DELETE')

    @property
    def schedules(self):
        return self.request_to_property('/schedules', Schedule)

    def create_schedule(self, schedule):
        if isinstance(schedule, Schedule):
            data = schedule.serialize()
        else:
            data = schedule

        return self.request('/schedules', method='POST',
                            data=json.dumps(data))

    def modify_schedule(self, schedule):
        return self.request('/schedules/{0}'.format(schedule.schedule_id),
                            method='PUT',
                            data=json.dumps(schedule.serialize()))

    def delete_schedule(self, schedule):
        return self.request('/schedules/{0}'.format(schedule.schedule_id),
                            method='DELETE')

    @property
    def scenes(self):
        return self.request_to_property('/scenes', Scene)

    def create_scene(self, name, lights):
        hashed = hashlib.sha256(name.encode('utf-8')).hexdigest()[:9]
        scene_id = '{}-on-0'.format(hashed)
        data = {'name': name, 'lights': lights}
        return self.request('/scenes/{}'.format(scene_id), method='PUT',
                            data=json.dumps(data))

    def modify_scene_light(self, scene, light, state):
        return self.request(
            '/scenes/{scene}/lights/{light}/state'.format(
                scene=scene.scene_id,
                light=light.light_id),
            method='PUT',
            data=json.dumps(state))

    @property
    def sensors(self):
        return self.request_to_property('/sensors', Sensor)

    @property
    def rules(self):
        return self.request_to_property('/rules', Rule)

    def modify_rule(self, rule):
        return self.request('/rules/{0}'.format(rule.rule_id),
                            method='PUT',
                            data=json.dumps(rule.serialize()))

    def delete_rule(self, rule):
        return self.request('/rules/{0}'.format(rule.rule_id),
                            method='DELETE')

    def delete_whitelist_entry(self, username):
        return self.request('/config/whitelist/{0}'.format(username),
                            method='DELETE')

    @property
    def config(self):
        return self.request('/config')

    def request_to_property(self, path, propobj):
        return {k: propobj(k, s) for k, s in self.request(path).items()}


class HueObject(object):
    def __init__(self, data, keys=None):
        self.keys = keys
        self.data = data

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        elif name in self.data:
            return self.data[name]
        else:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        if 'data' in self.__dict__ and name in self.data:
            self.data[name] = value
        else:
            super().__setattr__(name, value)

    def serialize(self):
        return self.data


class ColorLight(HueObject):
    def __init__(self, light_id, light):
        self.light_id = int(light_id)
        super().__init__(light)

    def __repr__(self):
        return 'ColorLight' + str(self.serialize())


class ExtendedColorLight(ColorLight):
    def __repr__(self):
        return 'ExtendedColorLight' + str(self.serialize())


class Group(HueObject):
    def __init__(self, group_id, group):
        self.group_id = int(group_id)
        super().__init__(group)

    def __repr__(self):
        return 'Group' + str(self.serialize())


class Schedule(HueObject):
    def __init__(self, schedule_id, schedule):
        self.schedule_id = int(schedule_id)
        super().__init__(schedule)

    def __repr__(self):
        return 'Schedule' + str(self.serialize())


class Scene(HueObject):
    def __init__(self, scene_id, scene):
        self.scene_id = scene_id
        super().__init__(scene)

    def __repr__(self):
        return 'Scene' + str(self.serialize())


class Sensor(HueObject):
    def __init__(self, sensor_id, sensor):
        self.sensor_id = int(sensor_id)
        super().__init__(sensor)

    def __repr__(self):
        return 'Sensor' + str(self.serialize())


class Rule(HueObject):
    def __init__(self, rule_id, rule):
        self.rule_id = int(rule_id)
        super().__init__(rule)

    def __repr__(self):
        return 'Rule' + str(self.serialize())
