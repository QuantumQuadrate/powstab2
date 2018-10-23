from worker import Worker
import dac8532.DAC8532 as dac


class WDAC8532(Worker):
    type = 'DAC8532'

    def setup(self):
        self.output = 2.0  # start rf attentuator mostly open
        if self.address > 1 or self.address < 0:
            self.logger.error('DAC8532 address: `{}` is out of range.'.format(self.address))
        self.update_output()  # push starting output to dac

    def update_output(self):
        if self.output > 5.0:
            out = 5.0
            self.output = 5.0
        elif self.output < 0.0:
            out = 0.0
            self.output = 0.0
        else:
            out = self.output
        try:
            # TODO: check return value to see if output is out of range
            # if it is propagate it back here so that if the controller rails
            # it doesn't just keep accumulating a non-physical output.
            dac.set_voltage(self.address, out)
        except IOError:
            self.exception("""A communication issue occured updating the DAC.
                    Reverting output variable.""")
            self.output -= self.delta
        self.ready = True
