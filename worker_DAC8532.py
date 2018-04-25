from worker import Worker
import dac8532.DAC8532 as dac


class WDAC8532(Worker):
    type = 'DAC8532'

    def setup(self):
        self.output = 5  # start rf attentuator open all the way (5 V)
        if self.address > 1 or self.address < 0:
            self.logger.error('DAC8532 address: `{}` is out of range.'.format(self.address))
        self.update_output()  # push starting output to dac

    def update_output(self):
        try:
            dac.set_voltage(self.address, self.output)
        except IOError:
            self.exception('A communication issue occured updating the DAC. Reverting output variable.')
            self.output -= self.delta
        self.ready = True
