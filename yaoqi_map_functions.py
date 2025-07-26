    def run_ditu4(self, character_grid, door_states, game_window, chenghao_box, monsters, skill_availability):
        """执行 ditu4 的跑图逻辑，移动 chenghao"""
        print(f"执行 ditu4 逻辑，人物位置: {character_grid}, chenghao_box: {chenghao_box}")
        if self.move_chenghao_to_target(game_window, chenghao_box, monsters, None, None, skill_availability):
            return
        if character_grid == "1-2" and (door_states.get("1-2") == "open" or door_states.get("1-3") == "open"):
            print("ditu4: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability)
        elif character_grid == "1-7" and door_states.get("2-7") == "open":
            print("ditu4: 触发移动到 (644, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 644, 516, skill_availability)
        elif character_grid == "2-7" and door_states.get("2-6") == "open":
            print("ditu4: 触发移动到 (137, 451)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 137, 451, skill_availability)
        elif character_grid == "2-6" and door_states.get("2-5") == "open":
            print("ditu4: 触发移动到 (68, 400)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 68, 400, skill_availability)
        elif character_grid == "2-5" and door_states.get("3-5") == "open":
            print("ditu4: 触发移动到 (600, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 600, 516, skill_availability)
        elif character_grid == "2-1" and (door_states.get("2-1") == "open" or door_states.get("2-2") == "open"):
            print("ditu4: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability)
        elif character_grid == "3-5" and door_states.get("3-6") == "open":
            print("ditu4: 触发移动到 (1015, 466)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1015, 466, skill_availability)
        elif character_grid == "3-6" and door_states.get("3-5") == "open":
            print("ditu4: 触发移动到 (1050, 409)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1050, 409, skill_availability)

    def run_ditu5(self, character_grid, door_states, game_window, chenghao_box, monsters, skill_availability):
        """执行 ditu5 的跑图逻辑，移动 chenghao"""
        print(f"执行 ditu5 逻辑，人物位置: {character_grid}, chenghao_box: {chenghao_box}")
        if self.move_chenghao_to_target(game_window, chenghao_box, monsters, None, None, skill_availability):
            return
        if character_grid == "1-2" and (door_states.get("1-2") == "open" or door_states.get("1-3") == "open"):
            print("ditu5: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability)
        elif character_grid == "1-3" and (door_states.get("1-2") == "open" or door_states.get("2-3") == "open"):
            print("ditu5: 触发移动到 (644, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 644, 516, skill_availability)
        elif character_grid == "2-3" and door_states.get("1-3") == "open":
            print("ditu5: 触发移动到 (137, 451)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 137, 451, skill_availability)
        elif character_grid == "2-6" and door_states.get("2-5") == "open":
            print("ditu5: 触发移动到 (68, 400)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 68, 400, skill_availability)
        elif character_grid == "2-5" and door_states.get("3-5") == "open":
            print("ditu5: 触发移动到 (600, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 600, 516, skill_availability)
        elif character_grid == "3-5" and door_states.get("3-6") == "open":
            print("ditu5: 触发移动到 (1015, 466)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1015, 466, skill_availability)
        elif character_grid == "3-6" and door_states.get("3-5") == "open":
            print("ditu5: 触发移动到 (1050, 409)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1050, 409, skill_availability)

    def run_ditu6(self, character_grid, door_states, game_window, chenghao_box, monsters, skill_availability):
        """执行 ditu6 的跑图逻辑，移动 chenghao"""
        print(f"执行 ditu6 逻辑，人物位置: {character_grid}, chenghao_box: {chenghao_box}")
        if self.move_chenghao_to_target(game_window, chenghao_box, monsters, None, None, skill_availability):
            return
        if character_grid == "1-2" and (door_states.get("1-2") == "open" or door_states.get("1-3") == "open"):
            print("ditu6: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability)
        elif character_grid == "1-3" and (door_states.get("1-2") == "open" or door_states.get("1-4") == "open"):
            print("ditu6: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability)
        elif character_grid == "1-4" and (door_states.get("1-3") == "open" or door_states.get("1-5") == "open"):
            print("ditu6: 触发移动到 (1011, 197)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1011, 197, skill_availability)
        elif character_grid == "1-5" and (door_states.get("1-4") == "open" or door_states.get("1-6") == "open"):
            print("ditu6: 触发移动到 (1028, 326)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1028, 326, skill_availability)
        elif character_grid == "1-6" and (door_states.get("1-5") == "open" or door_states.get("2-6") == "open"):
            print("ditu6: 触发移动到 (600, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 600, 516, skill_availability)
        elif character_grid == "2-6" and (door_states.get("1-6") == "open" or door_states.get("2-7") == "open"):
            print("ditu6: 触发移动到 (1015, 466)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1015, 466, skill_availability)
        elif character_grid == "2-7" and door_states.get("2-6") == "open":
            print("ditu6: 触发移动到 (500, 264)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 500, 264, skill_availability)

    def run_ditu7(self, character_grid, door_states, game_window, chenghao_box, monsters, skill_availability):
        """执行 ditu7 的跑图逻辑，移动 chenghao"""
        print(f"执行 ditu7 逻辑，人物位置: {character_grid}, chenghao_box: {chenghao_box}")
        if self.move_chenghao_to_target(game_window, chenghao_box, monsters, None, None, skill_availability):
            return
        if character_grid == "1-2" and (door_states.get("1-2") == "open" or door_states.get("1-3") == "open"):
            print("ditu7: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability)
        elif character_grid == "1-7" and door_states.get("2-7") == "open":
            print("ditu7: 触发移动到 (644, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 644, 516, skill_availability)
        elif character_grid == "2-7" and door_states.get("2-6") == "open":
            print("ditu7: 触发移动到 (137, 451)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 137, 451, skill_availability)
        elif character_grid == "2-6" and door_states.get("2-5") == "open":
            print("ditu7: 触发移动到 (68, 400)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 68, 400, skill_availability)
        elif character_grid == "2-5" and door_states.get("3-5") == "open":
            print("ditu7: 触发移动到 (600, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 600, 516, skill_availability)
        elif character_grid == "3-5" and door_states.get("3-6") == "open":
            print("ditu7: 触发移动到 (1015, 466)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1015, 466, skill_availability)
        elif character_grid == "3-6" and door_states.get("3-5") == "open":
            print("ditu7: 触发移动到 (1050, 409)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1050, 409, skill_availability)

    def run_ditu8(self, character_grid, door_states, game_window, chenghao_box, monsters, skill_availability):
        """执行 ditu8 的跑图逻辑，移动 chenghao"""
        print(f"执行 ditu8 逻辑，人物位置: {character_grid}, chenghao_box: {chenghao_box}")
        if self.move_chenghao_to_target(game_window, chenghao_box, monsters, None, None, skill_availability):
            return
        if character_grid == "1-2" and (door_states.get("1-2") == "open" or door_states.get("1-3") == "open"):
            print("ditu8: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability)
        elif character_grid == "1-6" and (door_states.get("1-6") == "open" or door_states.get("1-7") == "open"):
            print("ditu8: 741移动到 (1015, 466)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1015, 466, skill_availability)
        elif character_grid == "1-7" and door_states.get("2-7") == "open":
            print("ditu8: 触发移动到 (644, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 644, 516, skill_availability)
        elif character_grid == "2-7" and door_states.get("2-6") == "open":
            print("ditu8: 触发移动到 (137, 451)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 137, 451, skill_availability)
        elif character_grid == "2-6" and door_states.get("2-5") == "open":
            print("ditu8: 触发移动到 (68, 400)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 68, 400, skill_availability)
        elif character_grid == "2-5" and door_states.get("3-5") == "open":
            print("ditu8: 触发移动到 (600, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 600, 516, skill_availability)
        elif character_grid == "3-5" and door_states.get("3-6") == "open":
            print("ditu8: 触发移动到 (1015, 466)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1015, 466, skill_availability)
        elif character_grid == "3-6" and door_states.get("3-5") == "open":
            print("ditu8: 触发移动到 (1050, 409)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1050, 409, skill_availability)