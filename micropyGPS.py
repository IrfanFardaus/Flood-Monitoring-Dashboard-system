# MicropyGPS (Memory-Optimized Version)
# Stripped down for ESP32 RAM conservation. Only parses GGA and RMC.

class MicropyGPS(object):
    SENTENCE_LIMIT = 90
    __HEMISPHERES = ('N', 'S', 'E', 'W')

    def __init__(self, local_offset=0):
        # Object Status Flags
        self.sentence_active = False
        self.active_segment = 0
        self.process_crc = False
        self.gps_segments = []
        self.crc_xor = 0
        self.char_count = 0

        # Data From Sentences
        self.timestamp = [0, 0, 0.0]
        self.local_offset = local_offset
        self._latitude = [0, 0.0, 'N']
        self._longitude = [0, 0.0, 'W']
        self.fix_stat = 0
        self.valid = False

    @property
    def latitude(self):
        """Returns Latitude as a clean decimal float"""
        decimal_degrees = self._latitude[0] + (self._latitude[1] / 60.0)
        return decimal_degrees if self._latitude[2] == 'N' else -decimal_degrees

    @property
    def longitude(self):
        """Returns Longitude as a clean decimal float"""
        decimal_degrees = self._longitude[0] + (self._longitude[1] / 60.0)
        return decimal_degrees if self._longitude[2] == 'E' else -decimal_degrees

    def gprmc(self):
        """Parse Recommended Minimum Specific GPS/Transit data (RMC)"""
        try:
            utc_string = self.gps_segments[1]
            if utc_string:
                hours = (int(utc_string[0:2]) + self.local_offset) % 24
                minutes = int(utc_string[2:4])
                seconds = float(utc_string[4:])
                self.timestamp = [hours, minutes, seconds]
        except ValueError:
            return False

        if self.gps_segments[2] == 'A': 
            try:
                l_string = self.gps_segments[3]
                lat_degs = int(l_string[0:2])
                lat_mins = float(l_string[2:])
                lat_hemi = self.gps_segments[4]

                l_string = self.gps_segments[5]
                lon_degs = int(l_string[0:3])
                lon_mins = float(l_string[3:])
                lon_hemi = self.gps_segments[6]
            except ValueError:
                return False

            if lat_hemi not in self.__HEMISPHERES or lon_hemi not in self.__HEMISPHERES:
                return False

            self._latitude = [lat_degs, lat_mins, lat_hemi]
            self._longitude = [lon_degs, lon_mins, lon_hemi]
            self.fix_stat = 1
            self.valid = True
        else:
            self.valid = False
            self.fix_stat = 0

        return True

    def gpgga(self):
        """Parse Global Positioning System Fix Data (GGA)"""
        try:
            utc_string = self.gps_segments[1]
            if utc_string:
                hours = (int(utc_string[0:2]) + self.local_offset) % 24
                minutes = int(utc_string[2:4])
                seconds = float(utc_string[4:])
                self.timestamp = [hours, minutes, seconds]

            fix_stat = int(self.gps_segments[6])
        except (ValueError, IndexError):
            return False

        if fix_stat:
            try:
                l_string = self.gps_segments[2]
                lat_degs = int(l_string[0:2])
                lat_mins = float(l_string[2:])
                lat_hemi = self.gps_segments[3]

                l_string = self.gps_segments[4]
                lon_degs = int(l_string[0:3])
                lon_mins = float(l_string[3:])
                lon_hemi = self.gps_segments[5]
            except ValueError:
                return False

            if lat_hemi not in self.__HEMISPHERES or lon_hemi not in self.__HEMISPHERES:
                return False

            self._latitude = [lat_degs, lat_mins, lat_hemi]
            self._longitude = [lon_degs, lon_mins, lon_hemi]

        self.fix_stat = fix_stat
        if fix_stat > 0:
             self.valid = True
        else:
             self.valid = False

        return True

    def new_sentence(self):
        self.gps_segments = ['']
        self.active_segment = 0
        self.crc_xor = 0
        self.sentence_active = True
        self.process_crc = True
        self.char_count = 0

    def update(self, new_char):
        valid_sentence = False
        ascii_char = ord(new_char)

        if 10 <= ascii_char <= 126:
            self.char_count += 1

            if new_char == '$':
                self.new_sentence()
                return None
            elif self.sentence_active:
                if new_char == '*':
                    self.process_crc = False
                    self.active_segment += 1
                    self.gps_segments.append('')
                    return None
                elif new_char == ',':
                    self.active_segment += 1
                    self.gps_segments.append('')
                else:
                    self.gps_segments[self.active_segment] += new_char
                    if not self.process_crc:
                        if len(self.gps_segments[self.active_segment]) == 2:
                            try:
                                final_crc = int(self.gps_segments[self.active_segment], 16)
                                if self.crc_xor == final_crc:
                                    valid_sentence = True
                            except ValueError:
                                pass 

                if self.process_crc:
                    self.crc_xor ^= ascii_char

                if valid_sentence:
                    self.sentence_active = False 
                    if self.gps_segments[0] in self.supported_sentences:
                        if self.supported_sentences[self.gps_segments[0]](self):
                            return self.gps_segments[0]

                if self.char_count > self.SENTENCE_LIMIT:
                    self.sentence_active = False

        return None

    # Only support the two sentences that provide core location data
    supported_sentences = {
        'GPRMC': gprmc, 'GLRMC': gprmc, 'GNRMC': gprmc,
        'GPGGA': gpgga, 'GLGGA': gpgga, 'GNGGA': gpgga
    }